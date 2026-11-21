//! Offline prototype for an explicitly marked fixture; it does not replace the installed service.
use serde_json::{Map, Value, json};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read};
use std::os::unix::fs::FileExt;
use std::os::fd::{AsRawFd, FromRawFd, IntoRawFd};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

const RING_BYTES: u64 = 4 * 1024 * 1024;
const HEADER_BYTES: u64 = 4096;
const SLOT_BYTES: usize = 1024;
const SLOT_COUNT: u64 = (RING_BYTES - HEADER_BYTES) / SLOT_BYTES as u64;
const RING_FORMAT: &str = "bb-ultimo-aliento-anillo/1";
const STATE_FORMAT: &str = "bb-estado-maquina/1";
const STATE_MAX_AGE_S: f64 = 5.0;
const PSI_RESOURCES: [&str; 3] = ["cpu", "memory", "io"];
const MEM_KEYS: [&str; 5] = ["MemAvailable", "MemFree", "SwapTotal", "SwapFree", "Dirty"];
const FIXTURE_MARKER: &str = "blackbox-captura-observacion-fixture/1";

pub struct WriteFailure {
    pub record: Value,
    pub error: String,
}

pub fn write_record(file: &File, offset: u64, slot_bytes: usize, record: &Value) -> Result<(), WriteFailure> {
    let mut line = match serde_json::to_vec(record) {
        Ok(bytes) => bytes,
        Err(error) => return Err(WriteFailure { record: record.clone(), error: error.to_string() }),
    };
    if line.len() >= slot_bytes {
        return Err(WriteFailure { record: record.clone(), error: "registro supera la ranura".into() });
    }
    line.resize(slot_bytes - 1, b' ');
    line.push(b'\n');
    match file.write_at(&line, offset) {
        Ok(written) if written == slot_bytes => Ok(()),
        Ok(written) => Err(WriteFailure { record: record.clone(), error: format!("escritura parcial: {written}/{slot_bytes}") }),
        Err(error) => Err(WriteFailure { record: record.clone(), error: error.to_string() }),
    }
}

fn value_error(error: impl std::fmt::Display) -> Value {
    Value::String(error.to_string())
}

fn read_text(path: &Path) -> io::Result<String> {
    let metadata = fs::metadata(path)?;
    if !metadata.is_file() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "fuente no es archivo regular"));
    }
    let mut bytes = Vec::with_capacity(4096);
    File::open(path)?.take(65_537).read_to_end(&mut bytes)?;
    if bytes.len() > 65_536 {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "fuente supera 65536 bytes"));
    }
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

fn corto(error: impl std::fmt::Display) -> String {
    let s = error.to_string();
    s.chars().take(96).collect()
}

fn open_confined(root: &Path, path: &Path, directory: bool) -> io::Result<File> {
    let canonical = path.canonicalize()?;
    let relative = canonical.strip_prefix(root)
        .map_err(|_| io::Error::new(io::ErrorKind::PermissionDenied, "fuente fuera del fixture"))?;
    let root_name = std::ffi::CString::new(root.as_os_str().as_bytes())
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "ruta fixture invalida"))?;
    let root_fd = unsafe { libc::open(root_name.as_ptr(), libc::O_RDONLY | libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC) };
    if root_fd < 0 { return Err(io::Error::last_os_error()); }
    let mut current = unsafe { File::from_raw_fd(root_fd) };
    let components: Vec<_> = relative.components().collect();
    if components.is_empty() {
        if directory { return Ok(current); }
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "fuente no es archivo regular"));
    }
    for (index, component) in components.iter().enumerate() {
        let std::path::Component::Normal(name) = component else {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "ruta fuente invalida"));
        };
        let name = std::ffi::CString::new(name.as_bytes())
            .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "nombre fuente invalido"))?;
        let last = index + 1 == components.len();
        let mut flags = libc::O_RDONLY | libc::O_NOFOLLOW | libc::O_CLOEXEC;
        if last && !directory { flags |= libc::O_NONBLOCK; }
        if !last || directory { flags |= libc::O_DIRECTORY; }
        let fd = unsafe { libc::openat(current.as_raw_fd(), name.as_ptr(), flags) };
        if fd < 0 { return Err(io::Error::last_os_error()); }
        current = unsafe { File::from_raw_fd(fd) };
    }
    let metadata = current.metadata()?;
    if (directory && !metadata.is_dir()) || (!directory && !metadata.is_file()) {
        return Err(io::Error::new(io::ErrorKind::InvalidInput,
            if directory { "fuente no es directorio" } else { "fuente no es archivo regular" }));
    }
    Ok(current)
}

fn read_confined(root: &Path, path: &Path) -> io::Result<String> {
    let mut bytes = Vec::with_capacity(4096);
    open_confined(root, path, false)?.take(65_537).read_to_end(&mut bytes)?;
    if bytes.len() > 65_536 {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "fuente supera 65536 bytes"));
    }
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

fn read_psi(root: &Path, resource: &str) -> Result<Value, String> {
    let path = root.join("proc/pressure").join(resource);
    let text = read_confined(root, &path).map_err(|e| corto(e))?;
    let mut values = Map::new();
    for line in text.lines() {
        let mut parts = line.split_whitespace();
        let Some(kind @ ("some" | "full")) = parts.next() else { continue };
        let fields: std::collections::HashMap<_, _> = parts.filter_map(|p| p.split_once('=')).collect();
        let parse = |key: &str| fields.get(key).ok_or_else(|| format!("falta {key}"));
        let avg10: f64 = parse("avg10")?.parse().map_err(|e: std::num::ParseFloatError| e.to_string())?;
        let avg60: f64 = parse("avg60")?.parse().map_err(|e: std::num::ParseFloatError| e.to_string())?;
        let avg300: f64 = parse("avg300")?.parse().map_err(|e: std::num::ParseFloatError| e.to_string())?;
        if !avg10.is_finite() || !avg60.is_finite() || !avg300.is_finite() {
            return Err("non-finite PSI value".into());
        }
        let total: u64 = parse("total")?.parse().map_err(|e: std::num::ParseIntError| e.to_string())?;
        values.insert(kind.into(), json!([avg10, avg60, avg300, total]));
    }
    if !values.contains_key("some") { return Err("sin linea some".into()); }
    Ok(Value::Object(values))
}

fn read_meminfo(root: &Path) -> Result<Value, String> {
    let text = read_confined(root, &root.join("proc/meminfo")).map_err(|e| corto(e))?;
    let mut values = Map::new();
    for line in text.lines() {
        let Some((key, rest)) = line.split_once(':') else { continue };
        if MEM_KEYS.contains(&key) {
            let first = rest.split_whitespace().next().ok_or_else(|| format!("valor vacio {key}"))?;
            let number = first.parse::<u64>().map_err(|e| e.to_string())?;
            values.insert(key.into(), json!(number));
        }
    }
    let missing: Vec<_> = MEM_KEYS.iter().filter(|key| !values.contains_key(**key)).copied().collect();
    if !missing.is_empty() { return Err(format!("faltan {}", missing.join(","))); }
    Ok(Value::Object(values))
}

fn zone_sort(a: &str, b: &str) -> std::cmp::Ordering {
    let number = |s: &str| s.strip_prefix("thermal_zone").and_then(|n| n.parse::<u64>().ok());
    match (number(a), number(b)) {
        (Some(x), Some(y)) => x.cmp(&y),
        (Some(_), None) => std::cmp::Ordering::Less,
        (None, Some(_)) => std::cmp::Ordering::Greater,
        (None, None) => a.cmp(b),
    }
}

fn discover_zones(root: &Path) -> Vec<(String, PathBuf)> {
    let thermal = root.join("sys/class/thermal");
    let Ok(directory) = open_confined(root, &thermal, true) else { return Vec::new(); };
    let raw = directory.into_raw_fd();
    let dir = unsafe { libc::fdopendir(raw) };
    if dir.is_null() {
        unsafe { libc::close(raw); }
        return Vec::new();
    }
    let mut zones = Vec::new();
    loop {
        let entry = unsafe { libc::readdir(dir) };
        if entry.is_null() { break; }
        let name = unsafe { std::ffi::CStr::from_ptr((*entry).d_name.as_ptr()) };
        let name = std::ffi::OsString::from_vec(name.to_bytes().to_vec());
        if name.to_string_lossy().starts_with("thermal_zone") {
            zones.push(thermal.join(name));
        }
    }
    unsafe { libc::closedir(dir); }
    zones.sort_by(|a, b| zone_sort(&a.file_name().unwrap().to_string_lossy(), &b.file_name().unwrap().to_string_lossy()));
    zones.into_iter().map(|zone| {
        let name = zone.file_name().unwrap().to_string_lossy().to_string();
        let key = name.strip_prefix("thermal_zone").unwrap_or(&name).to_string();
        (key, zone.join("temp"))
    }).collect()
}

fn capture(root: &Path, zones: &[(String, PathBuf)], boot: &str, ts: f64, seq: u64,
           state_check: Option<&Path>, now: f64) -> Value {
    let mut record = Map::new();
    record.insert("seq".into(), json!(seq));
    record.insert("ts".into(), json!(ts));
    record.insert("boot".into(), json!(boot));
    record.insert("tipo".into(), json!("muestra"));
    let mut missing = Map::new();
    let mut psi = Map::new();
    for resource in PSI_RESOURCES {
        match read_psi(root, resource) {
            Ok(value) => { psi.insert(resource.into(), value); }
            Err(error) => { missing.insert(format!("psi_{resource}"), value_error(error)); }
        }
    }
    record.insert("psi".into(), Value::Object(psi));
    match read_meminfo(root) {
        Ok(value) => { record.insert("mem_kb".into(), value); }
        Err(error) => { missing.insert("meminfo".into(), value_error(error)); }
    }
    if zones.is_empty() {
        missing.insert("termica".into(), value_error(format!("sin thermal_zone* en {}", root.join("sys/class/thermal").display())));
    } else {
        let mut temps = Map::new();
        for (key, path) in zones {
            match read_confined(root, path).and_then(|s| s.trim().parse::<i64>().map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))) {
                Ok(milli) => { temps.insert(key.clone(), json!(milli as f64 / 1000.0)); }
                Err(error) => {
                    temps.insert(key.clone(), Value::Null);
                    missing.insert(format!("tz{key}"), value_error(corto(error)));
                }
            }
        }
        record.insert("temp_c".into(), Value::Object(temps));
    }
    match read_confined(root, &root.join("proc/loadavg")) {
        Ok(text) => {
            let parsed: Result<Vec<f64>, _> = text.split_whitespace().take(3).map(str::parse).collect();
            match parsed {
                Ok(values) if values.len() == 3 && values.iter().all(|v| v.is_finite()) => { record.insert("loadavg".into(), json!(values)); }
                Ok(_) => { missing.insert("loadavg".into(), value_error("non-finite loadavg value")); }
                _ => { missing.insert("loadavg".into(), value_error("formato invalido")); }
            }
        }
        Err(error) => { missing.insert("loadavg".into(), value_error(corto(error))); }
    }
    if let Some(path) = state_check {
        if let Err(error) = validate_state(root, path, now, STATE_MAX_AGE_S) {
            missing.insert("estado".into(), value_error(error));
        }
    }
    if !missing.is_empty() { record.insert("ausente".into(), Value::Object(missing)); }
    Value::Object(record)
}

pub fn validate_state(root: &Path, path: &Path, now: f64, max_age: f64) -> Result<(), String> {
    let text = read_confined(root, path).map_err(|e| corto(e))?;
    let value: Value = serde_json::from_str(&text).map_err(|e| corto(e))?;
    if value.get("formato").and_then(Value::as_str) != Some(STATE_FORMAT) {
        return Err(format!("formato distinto de {STATE_FORMAT}"));
    }
    let ts = value.get("ts").and_then(Value::as_f64).ok_or_else(|| "sin sello ts".to_string())?;
    let age = now - ts;
    if age > max_age { return Err(format!("sello viejo: {age:.1} s (max {max_age:.1} s)")); }
    if age < -max_age { return Err(format!("sello en el futuro: {:.1} s", -age)); }
    Ok(())
}

fn padded(value: &Value, len: usize) -> io::Result<Vec<u8>> {
    let mut data = serde_json::to_vec(value).map_err(io::Error::other)?;
    if data.len() >= len { return Err(io::Error::new(io::ErrorKind::InvalidData, "JSON supera cabecera")); }
    data.resize(len - 1, b' ');
    data.push(b'\n');
    Ok(data)
}

struct Ring { file: File, seq: u64 }

impl Ring {
    fn open(path: &Path) -> io::Result<Self> {
        if let Some(parent) = path.parent() { fs::create_dir_all(parent)?; }
        let file = OpenOptions::new().read(true).write(true).create_new(true).open(path)?;
        if file.metadata()?.len() == 0 {
            // posix_fallocate preserves the source ring's allocated-space contract.
            let rc = unsafe { libc::posix_fallocate(file.as_raw_fd(), 0, RING_BYTES as libc::off_t) };
            if rc != 0 { return Err(io::Error::from_raw_os_error(rc)); }
            let header = json!({"formato":RING_FORMAT,"tamano":RING_BYTES,"encabezado":HEADER_BYTES,
                "registro":SLOT_BYTES,"ranuras":SLOT_COUNT,"creado":now_seconds()});
            let bytes = padded(&header, HEADER_BYTES as usize)?;
            file.write_at(&bytes, 0)?;
            file.sync_data()?;
        }
        if file.metadata()?.len() != RING_BYTES { return Err(io::Error::new(io::ErrorKind::InvalidData, "geometria de anillo distinta")); }
        let mut header_bytes = vec![0; HEADER_BYTES as usize];
        file.read_at(&mut header_bytes, 0)?;
        let header: Value = serde_json::from_slice(&header_bytes).map_err(io::Error::other)?;
        if header["formato"] != RING_FORMAT || header["tamano"] != RING_BYTES ||
            header["encabezado"] != HEADER_BYTES || header["registro"] != SLOT_BYTES as u64 ||
            header["ranuras"] != SLOT_COUNT {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "cabecera de anillo invalida"));
        }
        let mut seq = 0;
        let mut slot = vec![0; SLOT_BYTES];
        for i in 0..SLOT_COUNT {
            file.read_at(&mut slot, HEADER_BYTES + i * SLOT_BYTES as u64)?;
            if slot.first() == Some(&0) { continue; }
            if let Ok(value) = serde_json::from_slice::<Value>(&slot) {
                if let Some(found) = value.get("seq").and_then(Value::as_u64) { seq = seq.max(found + 1); }
            }
        }
        Ok(Self { file, seq })
    }

    fn write(&mut self, record: &Value) -> Result<(), WriteFailure> {
        let offset = HEADER_BYTES + (self.seq % SLOT_COUNT) * SLOT_BYTES as u64;
        let mut value = record.clone();
        value["seq"] = json!(self.seq);
        write_record(&self.file, offset, SLOT_BYTES, &value)?;
        self.seq += 1;
        Ok(())
    }
}

fn now_seconds() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs_f64()
}

pub fn parse_peak_rss(status: &str) -> Result<f64, String> {
    let value = status.lines().find_map(|l| l.strip_prefix("VmHWM:")).ok_or("falta VmHWM")?;
    let kib = value.split_whitespace().next().ok_or("VmHWM vacio")?.parse::<f64>().map_err(|e| e.to_string())?;
    let mib = kib / 1024.0;
    if !mib.is_finite() || mib <= 0.0 { return Err("VmHWM invalido".into()); }
    Ok(mib)
}

fn peak_rss_mib() -> Result<f64, String> {
    let status = read_text(Path::new("/proc/self/status")).map_err(|e| corto(e))?;
    parse_peak_rss(&status)
}

fn percentile(values: &[f64], p: f64) -> f64 {
    if values.is_empty() { return 0.0; }
    let mut sorted = values.to_vec();
    sorted.sort_by(f64::total_cmp);
    sorted[((sorted.len() - 1) as f64 * p).floor() as usize]
}

fn parse_args(args: &[String]) -> Result<std::collections::HashMap<String, String>, String> {
    let allowed = ["--fixture", "--ring", "--samples", "--ts-base", "--step-seconds", "--state-check", "--now"];
    let mut parsed = std::collections::HashMap::new();
    let mut i = 0;
    while i < args.len() {
        let name = args[i].as_str();
        if !allowed.contains(&name) { return Err(format!("argumento desconocido: {name}")); }
        let value = args.get(i + 1).ok_or_else(|| format!("falta valor para {name}"))?;
        if value.starts_with("--") { return Err(format!("valor ausente para {name}")); }
        if parsed.insert(name.to_string(), value.clone()).is_some() { return Err(format!("argumento duplicado: {name}")); }
        i += 2;
    }
    Ok(parsed)
}

fn finite_arg(values: &std::collections::HashMap<String, String>, name: &str, fallback: f64) -> Result<f64, String> {
    let value = values.get(name).map(|v| v.parse::<f64>().map_err(|e| e.to_string())).transpose()?.unwrap_or(fallback);
    if !value.is_finite() { return Err(format!("valor no finito para {name}")); }
    Ok(value)
}

fn validate_fixture(path: &Path) -> Result<PathBuf, String> {
    let canonical = path.canonicalize().map_err(|e| format!("fixture: {}", corto(e)))?;
    if !canonical.is_dir() { return Err("fixture no es directorio".into()); }
    let marker = read_confined(&canonical, &canonical.join(".bb-capture-fixture")).map_err(|e| corto(e))?;
    if marker.trim() != FIXTURE_MARKER { return Err("fixture sin marcador aislado".into()); }
    Ok(canonical)
}

fn validate_destination(path: &Path) -> Result<(), String> {
    let home = env::var_os("HOME").ok_or("falta HOME")?;
    let allowed = PathBuf::from(home).join("scratch/blackbox");
    let requested = env::var_os("BB_CAPTURE_SCRATCH");
    let root = match allowed.canonicalize() {
        Ok(root) => root,
        Err(_error) if requested.is_none() => {
            fs::create_dir_all(&allowed).map_err(|e| corto(e))?;
            allowed.canonicalize().map_err(|e| corto(e))?
        }
        Err(error) => return Err(format!("HOME/scratch/blackbox: {}", corto(error))),
    };
    let scratch = if let Some(value) = requested {
        let requested = PathBuf::from(value);
        let canonical = requested.canonicalize().map_err(|e| format!("BB_CAPTURE_SCRATCH: {}", corto(e)))?;
        if !canonical.starts_with(&root) { return Err("BB_CAPTURE_SCRATCH fuera de HOME/scratch/blackbox".into()); }
        canonical
    } else { root.clone() };
    let root = scratch;
    let parent = path.parent().ok_or("destino sin directorio padre")?.canonicalize().map_err(|e| corto(e))?;
    if !parent.starts_with(root) { return Err("destino fuera de HOME/scratch/blackbox".into()); }
    if path.exists() { return Err("destino existente; se conserva evidencia previa".into()); }
    Ok(())
}

fn fail(message: &str, record: Option<&Value>) -> i32 {
    if let Some(value) = record { println!("{}", value); }
    eprintln!("COULD_NOT_RUN: {message}");
    2
}

fn run(args: &[String]) -> i32 {
    let values = match parse_args(args) { Ok(v) => v, Err(e) => return fail(&e, None) };
    let Some(fixture_path) = values.get("--fixture").map(PathBuf::from) else { return fail("falta --fixture", None); };
    let root = match validate_fixture(&fixture_path) { Ok(p) => p, Err(e) => return fail(&e, None) };
    let Some(ring_path) = values.get("--ring").map(PathBuf::from) else { return fail("falta --ring", None); };
    if let Err(error) = validate_destination(&ring_path) { return fail(&error, None); }
    let samples = match values.get("--samples").map(|v| v.parse::<usize>()).transpose() {
        Ok(Some(v @ 1..=4092)) => v,
        Ok(Some(_)) => return fail("--samples fuera del rango 1..4092", None),
        Ok(None) => return fail("falta --samples", None),
        Err(e) => return fail(&e.to_string(), None),
    };
    let ts_base = match finite_arg(&values, "--ts-base", now_seconds()) { Ok(v) => v, Err(e) => return fail(&e, None) };
    let step = match finite_arg(&values, "--step-seconds", 0.25) { Ok(v) if v > 0.0 => v, Ok(_) => return fail("--step-seconds debe ser positivo", None), Err(e) => return fail(&e, None) };
    if (0..samples).any(|i| !(ts_base + i as f64 * step).is_finite()) {
        return fail("timestamp derivado fuera de rango", None);
    }
    let mut state_check = values.get("--state-check").map(PathBuf::from);
    if let Some(path) = state_check.as_mut() {
        let checked = match path.canonicalize() { Ok(p) => p, Err(e) => return fail(&corto(e), None) };
        if !checked.starts_with(&root) { return fail("--state-check fuera del fixture", None); }
        if !checked.is_file() { return fail("--state-check no es archivo regular", None); }
        *path = checked;
    }
    let now = match finite_arg(&values, "--now", now_seconds()) { Ok(v) => v, Err(e) => return fail(&e, None) };
    let zones = discover_zones(&root);
    let boot = read_confined(&root, &root.join("proc/sys/kernel/random/boot_id"))
        .map(|s| s.trim().replace('-', ""))
        .unwrap_or_else(|_| "desconocido".into());
    let mut ring = match Ring::open(&ring_path) {
        Ok(ring) => ring,
        Err(error) => {
            let partial = capture(&root, &zones, &boot, ts_base, 0, state_check.as_deref(), now);
            return fail(&format!("open {}: {}", ring_path.display(), error), Some(&partial));
        }
    };
    let mut latencies = Vec::with_capacity(samples);
    let mut first = Value::Null;
    for i in 0..samples {
        let start = std::time::Instant::now();
        let record = capture(&root, &zones, &boot, ts_base + i as f64 * step, ring.seq, state_check.as_deref(), now);
        let result = ring.write(&record);
        latencies.push(start.elapsed().as_secs_f64() * 1000.0);
        if i == 0 { first = record.clone(); }
        if let Err(error) = result {
            return fail(&format!("write {}: {}", ring_path.display(), error.error), Some(&error.record));
        }
    }
    let peak_rss = match peak_rss_mib() {
        Ok(value) => value,
        Err(error) => return fail(&format!("memoria pico no medible: {error}"), Some(&first)),
    };
    let report = json!({"implementation":"rust-captura/1",
        "build_profile": if cfg!(debug_assertions) {"debug"} else {"release"},
        "samples":samples,
        "boot":first["boot"],"first_record":first,
        "latency_ms":{"p50":percentile(&latencies,0.50),"p95":percentile(&latencies,0.95),"max":latencies.iter().copied().fold(0.0,f64::max)},
        "peak_rss_mib":peak_rss,"ring":{"format":RING_FORMAT,"bytes":RING_BYTES,
            "header_bytes":HEADER_BYTES,"slot_bytes":SLOT_BYTES,"slots":SLOT_COUNT},
        "sync":"excluded; no periodic fdatasync in this prototype"});
    println!("{report}");
    0
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    std::process::exit(run(&args));
}

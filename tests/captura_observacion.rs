use serde_json::{Value, json};
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::os::unix::fs::MetadataExt;
use std::process::{Command, Output};
use std::time::{SystemTime, UNIX_EPOCH};
use std::sync::atomic::{AtomicU64, Ordering};
use std::ffi::CString;

#[allow(dead_code)]
#[path = "../rust/captura/main.rs"]
mod captura;

struct Scratch(PathBuf);

impl Scratch {
    fn new() -> Self {
        let allowed = PathBuf::from(std::env::var_os("HOME").expect("HOME is required"))
            .join("scratch/blackbox");
        let root = if let Some(override_root) = std::env::var_os("BB_CAPTURE_SCRATCH") {
            let allowed_canonical = allowed.canonicalize().expect("scratch root must exist");
            let root = PathBuf::from(override_root).canonicalize().expect("scratch override must exist");
            assert!(root.starts_with(allowed_canonical), "BB_CAPTURE_SCRATCH must stay under HOME/scratch/blackbox");
            root
        } else {
            fs::create_dir_all(&allowed).unwrap();
            allowed.canonicalize().unwrap()
        };
        let nonce = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let path = root.join(format!("captura-observacion-{}-{nonce}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn fixture() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/captura_observacion")
}

fn run(root: &Path, ring: &Path, samples: usize, extra: &[String]) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_captura-observacion"));
    let mut scratch_root = ring.parent().unwrap();
    while !scratch_root.is_dir() { scratch_root = scratch_root.parent().unwrap(); }
    command.env("BB_CAPTURE_SCRATCH", scratch_root);
    command.args(["--fixture", root.to_str().unwrap(), "--ring", ring.to_str().unwrap(),
                  "--samples", &samples.to_string(), "--ts-base", "1000000000", "--step-seconds", "0.25"]);
    command.args(extra);
    command.output().unwrap()
}

#[test]
fn derived_timestamp_overflow_is_rejected_before_evidence_creation() {
    let scratch = Scratch::new();
    let ring = scratch.0.join("overflow.bin");
    let out = Command::new(env!("CARGO_BIN_EXE_captura-observacion"))
        .env("BB_CAPTURE_SCRATCH", &scratch.0)
        .args(["--fixture", fixture().to_str().unwrap(), "--ring", ring.to_str().unwrap(),
            "--samples", "2", "--ts-base", "1e308", "--step-seconds", "1e308"])
        .output().unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&out.stderr).contains("timestamp derivado"));
    assert!(!ring.exists());
}

#[test]
fn marked_fixture_rejects_external_marker_symlink() {
    let scratch = Scratch::new();
    let outside = scratch.0.join("outside");
    fs::create_dir_all(&outside).unwrap();
    fs::write(outside.join("secret"), "synthetic outside value").unwrap();

    let marker_root = scratch.0.join("marker-fixture");
    copy_tree(&fixture(), &marker_root);
    fs::remove_file(marker_root.join(".bb-capture-fixture")).unwrap();
    std::os::unix::fs::symlink(outside.join("secret"), marker_root.join(".bb-capture-fixture")).unwrap();
    let marker_ring = scratch.0.join("marker-ring.bin");
    let out = run(&marker_root, &marker_ring, 1, &[]);
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&out.stderr).contains("fuera del fixture"));
    assert!(!marker_ring.exists());

}

#[test]
fn marked_fixture_rejects_external_psi_symlink() {
    let scratch = Scratch::new();
    let outside = scratch.0.join("outside");
    fs::create_dir_all(&outside).unwrap();
    fs::write(outside.join("memory"), "some avg10=42 avg60=40 avg300=38 total=100\nfull avg10=0 avg60=0 avg300=0 total=0\n").unwrap();
    let source_root = scratch.0.join("source-fixture");
    copy_tree(&fixture(), &source_root);
    fs::remove_file(source_root.join("proc/pressure/memory")).unwrap();
    std::os::unix::fs::symlink(outside.join("memory"), source_root.join("proc/pressure/memory")).unwrap();
    let source_ring = scratch.0.join("source-ring.bin");
    let out = run(&source_root, &source_ring, 1, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let row = &python_ring(&source_ring)["samples"][0];
    assert!(row.get("ausente").and_then(|missing| missing.get("psi_memory"))
        .and_then(Value::as_str).is_some_and(|error| error.contains("fuera del fixture")));
    assert!(row["psi"].get("memory").is_none());

    let ancestor_root = scratch.0.join("ancestor-fixture");
    copy_tree(&fixture(), &ancestor_root);
    fs::remove_dir_all(ancestor_root.join("proc/pressure")).unwrap();
    std::os::unix::fs::symlink(&outside, ancestor_root.join("proc/pressure")).unwrap();
    let ancestor_ring = scratch.0.join("ancestor-ring.bin");
    let out = run(&ancestor_root, &ancestor_ring, 1, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let row = &python_ring(&ancestor_ring)["samples"][0];
    assert!(row.get("ausente").and_then(|missing| missing.get("psi_memory"))
        .and_then(Value::as_str).is_some_and(|error| error.contains("fuera del fixture")));
    assert!(row["psi"].get("memory").is_none());
}

#[test]
fn scratch_override_escape_is_rejected_before_ring_creation() {
    let scratch = Scratch::new();
    let ring = scratch.0.join("escape.bin");
    let escape = PathBuf::from(std::env::var_os("HOME").unwrap()).join("scratch");
    let out = Command::new(env!("CARGO_BIN_EXE_captura-observacion"))
        .env("BB_CAPTURE_SCRATCH", &escape)
        .args(["--fixture", fixture().to_str().unwrap(), "--ring", ring.to_str().unwrap(),
            "--samples", "1", "--ts-base", "100", "--step-seconds", "1"])
        .output().unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&out.stderr).contains("BB_CAPTURE_SCRATCH fuera"));
    assert!(!ring.exists());

    let link = scratch.0.join("escape-link");
    std::os::unix::fs::symlink(PathBuf::from(std::env::var_os("HOME").unwrap()).join("scratch"), &link).unwrap();
    let linked_ring = scratch.0.join("symlink-escape.bin");
    let out = Command::new(env!("CARGO_BIN_EXE_captura-observacion"))
        .env("BB_CAPTURE_SCRATCH", &link)
        .args(["--fixture", fixture().to_str().unwrap(), "--ring", linked_ring.to_str().unwrap(),
            "--samples", "1", "--ts-base", "100", "--step-seconds", "1"])
        .output().unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&out.stderr).contains("BB_CAPTURE_SCRATCH fuera"));
    assert!(!linked_ring.exists());
}

#[test]
fn rejected_thermal_zone_is_reported_alongside_valid_zone() {
    let scratch = Scratch::new();
    let root = scratch.0.join("fixture");
    copy_tree(&fixture(), &root);
    let outside = scratch.0.join("outside-zone");
    fs::create_dir_all(&outside).unwrap();
    fs::write(outside.join("temp"), "99999\n").unwrap();
    std::os::unix::fs::symlink(&outside, root.join("sys/class/thermal/thermal_zone1")).unwrap();
    let ring = scratch.0.join("thermal.bin");
    let out = run(&root, &ring, 1, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let row = &python_ring(&ring)["samples"][0];
    assert_eq!(row["temp_c"]["0"], 93.0);
    assert!(row["ausente"]["tz1"].as_str().unwrap().contains("fuera del fixture"));
}

#[test]
fn thermal_root_symlink_is_rejected_before_enumeration() {
    let scratch = Scratch::new();
    let root = scratch.0.join("fixture");
    copy_tree(&fixture(), &root);
    let outside = scratch.0.join("outside-thermal");
    fs::create_dir_all(outside.join("thermal_zone0")).unwrap();
    fs::write(outside.join("thermal_zone0/temp"), "99999\n").unwrap();
    fs::remove_dir_all(root.join("sys/class/thermal")).unwrap();
    std::os::unix::fs::symlink(&outside, root.join("sys/class/thermal")).unwrap();
    let ring = scratch.0.join("thermal-root-link.bin");
    let out = run(&root, &ring, 1, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let row = &python_ring(&ring)["samples"][0];
    assert!(row["ausente"].get("termica").is_some());
    assert!(row.get("temp_c").is_none());
}

#[test]
fn fifo_fixture_source_is_rejected_without_waiting_for_a_writer() {
    let scratch = Scratch::new();
    let root = scratch.0.join("fixture");
    copy_tree(&fixture(), &root);
    let source = root.join("proc/pressure/memory");
    fs::remove_file(&source).unwrap();
    let encoded = CString::new(source.as_os_str().as_encoded_bytes()).unwrap();
    let result = unsafe { libc::mkfifo(encoded.as_ptr(), 0o600) };
    assert_eq!(result, 0);
    let ring = scratch.0.join("fifo.bin");
    let out = run(&root, &ring, 1, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let row = &python_ring(&ring)["samples"][0];
    assert!(row["ausente"]["psi_memory"].as_str().unwrap().contains("archivo regular"));
}

fn python_ring(path: &Path) -> Value {
    let code = r#"import json,sys; sys.path.insert(0,'.'); from tools import ultimo_aliento as u; r=u.leer_anillo(sys.argv[1]); print(json.dumps({'header':r['cabecera'],'seqs':[x['seq'] for x in r['registros']],'samples':[x for x in r['registros'] if x.get('tipo')=='muestra'],'ilegibles':r['ilegibles']},separators=(',',':')) )"#;
    let out = Command::new("python3").args(["-B", "-I", "-c", code, path.to_str().unwrap()]).output().unwrap();
    assert!(out.status.success(), "python reader failed: {}", String::from_utf8_lossy(&out.stderr));
    serde_json::from_slice(&out.stdout).unwrap()
}

fn python_baseline(ring: &Path) {
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/baseline_python.py");
    let out = Command::new("python3").args(["-B", "-I", script.to_str().unwrap(), "--fixture",
        fixture().to_str().unwrap(), "--ring", ring.to_str().unwrap(), "--samples", "256"]).output().unwrap();
    assert!(out.status.success(), "python baseline failed: {}", String::from_utf8_lossy(&out.stderr));
}

#[test]
fn python_baseline_refuses_existing_ring_or_previous_without_changing_sentinels() {
    let scratch = Scratch::new();
    let ring = scratch.0.join("invalid-existing.bin");
    let previous = PathBuf::from(format!("{}.previo", ring.display()));
    fs::write(&ring, b"ring sentinel").unwrap();
    fs::write(&previous, b"previous sentinel").unwrap();
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/baseline_python.py");
    let run = |target: &Path| Command::new("python3")
        .args(["-B", "-I", script.to_str().unwrap(), "--fixture",
            fixture().to_str().unwrap(), "--ring", target.to_str().unwrap(), "--samples", "1"])
        .output().unwrap();

    let out = run(&ring);
    assert_eq!(out.status.code(), Some(2));
    let report: Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(report["status"], "COULD_NOT_RUN");
    assert_eq!(fs::read(&ring).unwrap(), b"ring sentinel");
    assert_eq!(fs::read(&previous).unwrap(), b"previous sentinel");

    let fresh = scratch.0.join("fresh.bin");
    let fresh_previous = PathBuf::from(format!("{}.previo", fresh.display()));
    fs::write(&fresh_previous, b"previous sentinel two").unwrap();
    let out = run(&fresh);
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(serde_json::from_slice::<Value>(&out.stdout).unwrap()["status"], "COULD_NOT_RUN");
    assert!(!fresh.exists());
    assert_eq!(fs::read(&fresh_previous).unwrap(), b"previous sentinel two");

    let linked_target = scratch.0.join("linked-target.bin");
    fs::write(&linked_target, b"linked ring sentinel").unwrap();
    let linked_ring = scratch.0.join("linked-ring.bin");
    std::os::unix::fs::symlink(&linked_target, &linked_ring).unwrap();
    let out = run(&linked_ring);
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(serde_json::from_slice::<Value>(&out.stdout).unwrap()["status"], "COULD_NOT_RUN");
    assert!(fs::symlink_metadata(&linked_ring).unwrap().file_type().is_symlink());
    assert_eq!(fs::read(&linked_target).unwrap(), b"linked ring sentinel");

    let dangling_target = scratch.0.join("dangling.bin");
    let dangling_previous = PathBuf::from(format!("{}.previo", dangling_target.display()));
    std::os::unix::fs::symlink(scratch.0.join("missing-target"), &dangling_previous).unwrap();
    let out = run(&dangling_target);
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(serde_json::from_slice::<Value>(&out.stdout).unwrap()["status"], "COULD_NOT_RUN");
    assert!(!dangling_target.exists());
    assert!(fs::symlink_metadata(&dangling_previous).unwrap().file_type().is_symlink());
}

fn copy_tree(source: &Path, target: &Path) {
    fs::create_dir_all(target).unwrap();
    for item in fs::read_dir(source).unwrap() {
        let item = item.unwrap();
        let dest = target.join(item.file_name());
        if item.file_type().unwrap().is_dir() {
            copy_tree(&item.path(), &dest);
        } else {
            fs::copy(item.path(), dest).unwrap();
        }
    }
}

#[test]
fn ring_matches_authentic_python_reader_and_retains_every_sequence() {
    let scratch = Scratch::new();
    let baseline = scratch.0.join("python-ring.bin");
    let ring = scratch.0.join("rust-ring.bin");
    python_baseline(&baseline);
    let out = run(&fixture(), &ring, 256, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let report: Value = serde_json::from_slice(&out.stdout).unwrap();
    let stored = python_ring(&ring);
    let reference = python_ring(&baseline);
    assert_eq!(stored["ilegibles"], 0);
    assert_eq!(reference["ilegibles"], 0);
    assert_eq!(stored["seqs"], json!((0..256).collect::<Vec<_>>()));
    assert_eq!(reference["seqs"], stored["seqs"]);
    assert_eq!(stored["samples"].as_array().unwrap().len(), 256);
    for (python, rust) in reference["samples"].as_array().unwrap().iter()
        .zip(stored["samples"].as_array().unwrap()) {
        for field in ["seq", "boot", "ts", "tipo", "ausente", "psi", "mem_kb", "temp_c", "loadavg"] {
            assert_eq!(python[field], rust[field], "seq {} field {field}", rust["seq"]);
        }
    }
    assert_eq!(stored["samples"][0]["boot"], "0123456789abcdef0123456789abcdef");
    assert_eq!(stored["samples"][0]["ts"], 1_000_000_000.0);
    assert_eq!(stored["samples"][0]["psi"]["memory"]["some"], json!([2.5,1.25,0.2,223456]));
    assert_eq!(stored["samples"][0]["mem_kb"]["MemAvailable"], 60_115_000);
    assert_eq!(stored["samples"][0]["temp_c"]["0"], 93.0);
    assert_eq!(stored["samples"][0]["loadavg"], json!([3.1,2.05,1.0]));
    assert_eq!(report["build_profile"], "debug");
    assert!(report["latency_ms"]["p95"].as_f64().unwrap() <= 25.0);
    assert!(report["peak_rss_mib"].as_f64().unwrap() <= 48.0);
    assert_eq!(fs::metadata(&ring).unwrap().len(), 4 * 1024 * 1024);
    assert!(fs::metadata(&ring).unwrap().blocks() * 512 >= 4 * 1024 * 1024);
}

#[test]
fn unreadable_psi_is_reported_and_other_fields_survive() {
    let scratch = Scratch::new();
    let root = scratch.0.join("fixture");
    copy_tree(&fixture(), &root);
    fs::write(root.join("proc/pressure/memory"), "malformed input\n").unwrap();
    let ring = scratch.0.join("ring.bin");
    let out = run(&root, &ring, 1, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let stored = python_ring(&ring);
    let row = &stored["samples"][0];
    assert!(row["ausente"]["psi_memory"].as_str().unwrap().contains("sin linea some"));
    assert_eq!(row["mem_kb"]["MemAvailable"], 60_115_000);
    assert_eq!(row["temp_c"]["0"], 93.0);
}

#[test]
fn stale_source_is_declared_in_observe_mode_while_other_fields_survive() {
    let scratch = Scratch::new();
    let ring = scratch.0.join("ring.bin");
    let state = fixture().join("estado-viejo.json");
    let extra = vec!["--state-check".into(), state.display().to_string(), "--now".into(), "1006".into()];
    let out = run(&fixture(), &ring, 1, &extra);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let stored = python_ring(&ring);
    let row = &stored["samples"][0];
    assert!(row["ausente"]["estado"].as_str().unwrap().contains("sello viejo"));
    assert_eq!(row["mem_kb"]["MemAvailable"], 60_115_000);
    assert_eq!(row["temp_c"]["0"], 93.0);
}

#[test]
fn nonfinite_psi_is_declared_and_other_sources_survive() {
    let scratch = Scratch::new();
    let root = scratch.0.join("fixture");
    copy_tree(&fixture(), &root);
    fs::write(root.join("proc/pressure/memory"),
        "some avg10=NaN avg60=1.25 avg300=0.20 total=223456\nfull avg10=0 avg60=0 avg300=0 total=0\n").unwrap();
    let ring = scratch.0.join("ring.bin");
    let out = run(&root, &ring, 1, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let stored = python_ring(&ring);
    let row = &stored["samples"][0];
    assert!(row["ausente"]["psi_memory"].as_str().unwrap().contains("non-finite"));
    assert_eq!(row["mem_kb"]["MemAvailable"], 60_115_000);
    assert_eq!(row["temp_c"]["0"], 93.0);
}

#[test]
fn missing_fixture_is_rejected_without_falling_back_to_live_proc() {
    let out = Command::new(env!("CARGO_BIN_EXE_captura-observacion")).output().unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert!(out.stdout.is_empty());
    assert!(String::from_utf8_lossy(&out.stderr).contains("falta --fixture"));
}

#[test]
fn malformed_nonfinite_and_unbounded_arguments_are_rejected_before_opening_output() {
    let scratch = Scratch::new();
    for (name, samples, ts, step, expected) in [
        ("too-many", "4093", "1000000000", "0.25", "fuera del rango"),
        ("nan-time", "1", "NaN", "0.25", "no finito"),
        ("infinite-step", "1", "1000000000", "inf", "no finito"),
    ] {
        let ring = scratch.0.join(format!("{name}.bin"));
        let out = Command::new(env!("CARGO_BIN_EXE_captura-observacion"))
            .args(["--fixture", fixture().to_str().unwrap(), "--ring", ring.to_str().unwrap(),
                "--samples", samples, "--ts-base", ts, "--step-seconds", step])
            .output().unwrap();
        assert_eq!(out.status.code(), Some(2), "{name}");
        assert!(String::from_utf8_lossy(&out.stderr).contains(expected), "{name}: {}", String::from_utf8_lossy(&out.stderr));
        assert!(!ring.exists(), "{name} created an output despite invalid input");
    }
}

#[test]
fn oversized_source_is_declared_while_other_sources_survive() {
    let scratch = Scratch::new();
    let root = scratch.0.join("fixture");
    copy_tree(&fixture(), &root);
    fs::write(root.join("proc/meminfo"), "MemAvailable: 1 kB\n".repeat(10_000)).unwrap();
    let ring = scratch.0.join("ring.bin");
    let out = run(&root, &ring, 1, &[]);
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let row = &python_ring(&ring)["samples"][0];
    assert!(row["ausente"]["meminfo"].as_str().unwrap().contains("65536"));
    assert_eq!(row["psi"]["memory"]["some"], json!([2.5,1.25,0.2,223456]));
    assert_eq!(row["temp_c"]["0"], 93.0);
}

#[test]
fn existing_destination_is_preserved_and_refused() {
    let scratch = Scratch::new();
    let ring = scratch.0.join("existing.bin");
    fs::write(&ring, "pre-existing evidence").unwrap();
    let out = run(&fixture(), &ring, 1, &[]);
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&out.stderr).contains("destino existente"));
    assert_eq!(fs::read(ring).unwrap(), b"pre-existing evidence");
}

#[test]
fn output_open_failure_returns_partial_sample_and_declares_could_not_run() {
    let scratch = Scratch::new();
    let non_directory = scratch.0.join("not-a-directory");
    fs::write(&non_directory, "occupied").unwrap();
    let destination = non_directory.join("ring.bin");
    let out = run(&fixture(), &destination, 1, &[]);
    assert_eq!(out.status.code(), Some(2));
    let partial: Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(partial["boot"], "0123456789abcdef0123456789abcdef");
    assert_eq!(partial["temp_c"]["0"], 93.0);
    assert!(String::from_utf8_lossy(&out.stderr).contains("COULD_NOT_RUN"));
    assert!(String::from_utf8_lossy(&out.stderr).contains("open"));
}

#[test]
fn real_read_only_descriptor_write_failure_preserves_partial_record() {
    let scratch = Scratch::new();
    let path = scratch.0.join("readonly.bin");
    File::create(&path).unwrap().write_all(b"existing evidence").unwrap();
    let file = OpenOptions::new().read(true).open(&path).unwrap();
    let record = json!({"boot":"0123456789abcdef0123456789abcdef","tipo":"muestra","temp_c":{"0":93.0}});
    let failure = captura::write_record(&file, 0, 1024, &record).unwrap_err();
    assert!(failure.error.contains("Bad file descriptor"), "{}", failure.error);
    assert_eq!(failure.record, record);
}

#[test]
fn missing_peak_rss_is_an_instrument_failure_not_zero() {
    assert!(captura::parse_peak_rss("VmRSS: 100 kB\n").is_err());
}

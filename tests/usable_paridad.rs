#[path = "../rust/usable/main.rs"]
mod usable;

use serde_json::{Value, json};
use std::ffi::CString;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use usable::{
    ConfinementClass, ConfinementDecision, ConfinementMode, Outcome, Sample, SlicePressures, State,
    classify_pressures, confinement_decision, step, step_confinement,
};

#[derive(Clone, Copy)]
struct Input {
    psi: Option<f64>,
    probe: f64,
    mode: ConfinementMode,
    pressures: SlicePressures,
}

impl Input {
    fn json(self) -> Value {
        let mode = match self.mode {
            ConfinementMode::Off => "off",
            ConfinementMode::Observe => "observar",
            ConfinementMode::Act => "actuar",
        };
        json!({
            "psi": self.psi,
            "probe": self.probe,
            "mode": mode,
            "pressures": {
                "app": self.pressures.app,
                "docker": self.pressures.docker,
                "system": self.pressures.system
            }
        })
    }
}

fn sample(psi: Option<f64>) -> Input {
    Input {
        psi,
        probe: 0.001,
        mode: ConfinementMode::Off,
        pressures: SlicePressures {
            app: Some(50.0),
            docker: Some(2.0),
            system: Some(0.0),
        },
    }
}

fn scenario(name: &str) -> Vec<Input> {
    let high = Some(50.0);
    let low = Some(0.5);
    let mut steps = match name {
        "bajo_el_umbral" => vec![sample(low); 3],
        "racha_hasta_colapso" => vec![sample(high); 11],
        "ilegible_en_mitad_de_racha" => [
            vec![sample(high); 3],
            vec![sample(None)],
            vec![sample(high)],
        ]
        .concat(),
        "ilegible_con_colapso_declarado" => [
            vec![sample(high); 10],
            vec![sample(None)],
            vec![sample(high)],
        ]
        .concat(),
        "ilegible_sin_racha" => vec![sample(None), sample(low)],
        "sonda_fuera_de_plazo" => {
            let mut values = vec![sample(low), sample(high), sample(low)];
            values[0].probe = 301.0;
            values[1].probe = 301.0;
            values
        }
        "confinado_acaricia" => vec![sample(high); 12],
        "confinado_habria_acariciado" => vec![sample(high); 11],
        "recuperacion_tras_bajas" => [
            vec![sample(high); 10],
            vec![sample(low); 3],
            vec![sample(high)],
        ]
        .concat(),
        "una_baja_no_absuelve_colapso" => [
            vec![sample(high); 10],
            vec![sample(low)],
            vec![sample(high)],
        ]
        .concat(),
        "una_baja_no_absuelve_racha" => [
            vec![sample(high); 3],
            vec![sample(low)],
            vec![sample(high)],
            vec![sample(low)],
            vec![sample(high)],
        ]
        .concat(),
        _ => panic!("escenario desconocido: {name}"),
    };
    if name == "confinado_acaricia" {
        for input in &mut steps {
            input.mode = ConfinementMode::Act;
            input.pressures = SlicePressures {
                app: Some(50.0),
                docker: Some(0.0),
                system: Some(0.0),
            };
        }
    } else if name == "confinado_habria_acariciado" {
        for input in &mut steps {
            input.mode = ConfinementMode::Observe;
            input.pressures = SlicePressures {
                app: Some(50.0),
                docker: Some(0.0),
                system: Some(0.0),
            };
        }
    }
    steps
}

fn oracle_events(name: &str, inputs: &[Input]) -> Vec<Value> {
    const ORACLE: &str = r#"
import importlib.machinery, importlib.util, json, pathlib, sys
path, encoded, name = sys.argv[1], sys.argv[2], sys.argv[3]
rows = json.loads(encoded)
loader = importlib.machinery.SourceFileLoader('bb_usable_oracle', path)
spec = importlib.util.spec_from_loader('bb_usable_oracle', loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
events, index = [], -1
class Finished(Exception): pass
def sleep(_seconds):
    global index
    index += 1
    if index >= len(rows): raise Finished()
def probe(): return 0.002 if index < 0 else rows[index]['probe']
real_confined = module.paso_confinado
def confined(count):
    events.append(['confinado', count])
    action, new_count = real_confined(count)
    events.append(['confinado_result', new_count, action])
    return action, new_count
module.time.sleep = sleep
module.probe = probe
module.psi_memory_full_avg10 = lambda: rows[index]['psi']
module.notify = lambda state: events.append(['notify', state])
module.log = lambda line: events.append(['log', line])
module.latencia_x_ms = lambda: None
module.paso_escalon = lambda psi, state, ahora=None: (events.append(['escalon', psi]), state)[1]
module.paso_confinado = confined
module.modo_confinado = lambda: rows[index]['mode']
module.presiones_slices = lambda: rows[index]['pressures']
module.diagnostico_atasco = lambda: {'synthetic': True}
module._datos = lambda: pathlib.Path('/tmp/bb-usable-oracle-' + name)
module.origen_al_declarar_colapso = lambda sustained: events.append(['origen', sustained])
module.avisar_origen_no_cargado = lambda: events.append(['aviso_origen'])
module.protegidos_origen = lambda: 'protegidos: fijo'
try: module.main()
except Finished: pass
print(json.dumps(events, ensure_ascii=True, separators=(',', ':')))
"#;
    let encoded =
        serde_json::to_string(&inputs.iter().copied().map(Input::json).collect::<Vec<_>>())
            .expect("entradas serializables");
    let oracle_path = std::env::var("BB_ORACLE_PATH")
        .unwrap_or_else(|_| "/workspace/bin/bb-usable".to_owned());
    let output = Command::new("/usr/bin/python3")
        .args([
            "-B",
            "-I",
            "-c",
            ORACLE,
            &oracle_path,
            &encoded,
            name,
        ])
        .output()
        .unwrap_or_else(|error| instrument_failure(&format!("Python stdlib: {error}")));
    assert_output_success(&output, &format!("oráculo verdadero: {name}"));
    serde_json::from_slice(&output.stdout)
        .unwrap_or_else(|error| instrument_failure(&format!("JSON del main verdadero: {error}")))
}

fn assert_output_success(output: &Output, operation: &str) {
    if !output.status.success() {
        instrument_failure(&format!(
            "{operation}: rc={:?}; stdout={}; stderr={}",
            output.status.code(),
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        ));
    }
}

fn events_by_step(events: &[Value]) -> Vec<Vec<Value>> {
    let mut steps = Vec::new();
    let mut current: Option<Vec<Value>> = None;
    for event in events {
        if event[0] == "escalon" {
            if let Some(previous) = current.take() {
                steps.push(previous);
            }
            current = Some(vec![event.clone()]);
        } else if let Some(current) = current.as_mut() {
            current.push(event.clone());
        }
    }
    if let Some(last) = current {
        steps.push(last);
    }
    steps
}

fn expected_outcome(events: &[Value]) -> Outcome {
    let logs = events
        .iter()
        .filter_map(|event| (event[0] == "log").then(|| event[1].as_str()).flatten())
        .collect::<Vec<_>>();
    if logs
        .iter()
        .any(|line| line.contains("SONDA FUERA DE PLAZO"))
    {
        Outcome::LateProbe
    } else if logs.iter().any(|line| line.contains("PSI ILEGIBLE")) {
        Outcome::UnreadablePsi
    } else if logs
        .iter()
        .any(|line| line.contains("habria acariciado el watchdog"))
    {
        Outcome::ConfinedObserve
    } else if logs
        .iter()
        .any(|line| line.contains("ATASCO CONFINADO a app.slice:"))
    {
        Outcome::ConfinedActHypothetical
    } else if logs.iter().any(|line| line.contains("COLAPSO:")) {
        Outcome::Collapse
    } else if logs
        .iter()
        .any(|line| line.contains("UNA sonda no absuelve"))
    {
        Outcome::LowPsiRetainsStreak
    } else if logs
        .iter()
        .any(|line| line.contains("sondas seguidas") && line.contains("se corta"))
    {
        Outcome::Recovery
    } else if logs.iter().any(|line| line.contains("racha ")) {
        Outcome::HighPsi
    } else {
        Outcome::Healthy
    }
}

fn expected_pet(events: &[Value]) -> bool {
    events
        .iter()
        .any(|event| event == &json!(["notify", "WATCHDOG=1"]))
}

fn declared_streak(events: &[Value]) -> Option<usize> {
    for event in events {
        let Some(line) = event
            .get(1)
            .and_then(Value::as_str)
            .filter(|_| event[0] == "log")
        else {
            continue;
        };
        if line.contains(" se corta") {
            return Some(0);
        }
        if let Some(position) = line.find("racha ") {
            let suffix = &line[position + "racha ".len()..];
            if let Some(number) = suffix.split('/').next().and_then(|part| part.parse().ok()) {
                return Some(number);
            }
        }
        if let Some(position) = line.find("sostenido ") {
            let suffix = &line[position + "sostenido ".len()..];
            if let Some(seconds) = suffix
                .split('s')
                .next()
                .and_then(|part| part.parse::<usize>().ok())
            {
                return Some(seconds / 30);
            }
        }
    }
    None
}

fn declared_lows(events: &[Value]) -> Option<usize> {
    for event in events {
        let Some(line) = event
            .get(1)
            .and_then(Value::as_str)
            .filter(|_| event[0] == "log")
        else {
            continue;
        };
        if line.contains("UNA sonda no absuelve") {
            return Some(1);
        }
        if line.contains("2 sondas seguidas") && line.contains("se corta") {
            return Some(0);
        }
    }
    None
}

fn without_confinement_instrumentation(events: &[Value]) -> Vec<Value> {
    events
        .iter()
        .filter(|event| event[0] != "confinado" && event[0] != "confinado_result")
        .cloned()
        .collect()
}

fn event_sequence(events: &[Value], kind: &str) -> Vec<Value> {
    events
        .iter()
        .filter(|event| event[0] == kind)
        .cloned()
        .collect()
}

fn decision_name(decision: ConfinementDecision) -> &'static str {
    match decision {
        ConfinementDecision::Retain => "retiene",
        ConfinementDecision::WouldPet => "habria_acariciado",
        ConfinementDecision::PetInSimulation => "acaricia",
    }
}

fn compare_scenarios() -> Vec<String> {
    let recorded: Value =
        serde_json::from_str(include_str!("fixtures/bb_usable_caracterizacion.json"))
            .expect("fixture de caracterización válido");
    let names = [
        "bajo_el_umbral",
        "confinado_acaricia",
        "confinado_habria_acariciado",
        "ilegible_con_colapso_declarado",
        "ilegible_en_mitad_de_racha",
        "ilegible_sin_racha",
        "racha_hasta_colapso",
        "recuperacion_tras_bajas",
        "sonda_fuera_de_plazo",
        "una_baja_no_absuelve_colapso",
        "una_baja_no_absuelve_racha",
    ];
    let mut differences = Vec::new();
    let mut checked_steps = 0;
    for name in names {
        let inputs = scenario(name);
        let oracle = oracle_events(name, &inputs);
        let historic = &recorded[name];
        let historic_events = historic.as_array().expect("eventos históricos");
        if without_confinement_instrumentation(historic_events)
            != without_confinement_instrumentation(&oracle)
        {
            differences.push(format!(
                "{name}: efectos de main difieren de la caracterización guardada"
            ));
        }
        let historical_counts = event_sequence(historic_events, "confinado");
        let real_counts = event_sequence(&oracle, "confinado");
        let case_difference_start = differences.len();
        let case_steps = inputs.len();
        let expected = events_by_step(&oracle);
        let escalon_count = event_sequence(&oracle, "escalon").len();
        if escalon_count != inputs.len() {
            differences.push(format!(
                "{name}: escalón independiente observado {escalon_count}/{} pasos",
                inputs.len()
            ));
        }
        if expected.len() != inputs.len() {
            differences.push(format!(
                "{name}: main verdadero tiene {} pasos y entrada {}",
                expected.len(),
                inputs.len()
            ));
            continue;
        }
        let mut state = State::default();
        for (index, (events, input)) in expected.iter().zip(inputs).enumerate() {
            let result = step(
                &mut state,
                Sample {
                    psi_full_avg10: input.psi,
                    probe_seconds: input.probe,
                    confinement_mode: input.mode,
                    pressures: input.pressures,
                },
            );
            checked_steps += 1;
            let oracle_outcome = expected_outcome(events);
            let oracle_pet = expected_pet(events);
            let oracle_streak = declared_streak(events);
            let oracle_lows = declared_lows(events);
            let oracle_confined = events.iter().find(|event| event[0] == "confinado_result");
            let oracle_count = oracle_confined
                .and_then(|event| event[1].as_u64())
                .map(|count| count as usize);
            let oracle_action = oracle_confined.and_then(|event| event[2].as_str());
            let rust_action = result.confinement_decision.map(decision_name);
            if result.outcome != oracle_outcome
                || result.simulated_watchdog_notification != oracle_pet
                || oracle_streak.is_some_and(|count| count != result.sustained_high)
                || oracle_lows.is_some_and(|count| count != result.consecutive_lows)
                || oracle_count.is_some_and(|count| count != result.confined_steps)
                || oracle_action != rust_action
            {
                differences.push(format!(
                    "{name}[{}]: main={oracle_outcome:?}/notify={oracle_pet}/racha={oracle_streak:?}/bajas={oracle_lows:?}/confinado={oracle_count:?}/{oracle_action:?}; Rust={:?}/notify={}/racha={}/bajas={}/confinado={}/{rust_action:?}",
                    index + 1,
                    result.outcome,
                    result.simulated_watchdog_notification,
                    result.sustained_high,
                    result.consecutive_lows,
                    result.confined_steps
                ));
            }
        }
        eprintln!(
            "case={name} pasos={case_steps} discrepancias={} historical_stub_counter={historical_counts:?} real_step_counter={real_counts:?}",
            differences.len() - case_difference_start
        );
    }
    assert!(
        differences.is_empty(),
        "casos y pasos comparados={checked_steps}; discrepancias caso por caso:\n{}",
        differences.join("\n")
    );
    eprintln!(
        "oracle=bin/bb-usable:main casos={} pasos={checked_steps} discrepancias=0",
        names.len()
    );
    Vec::new()
}

fn detector_alias_controls() {
    let clean = "execve(\"/usr/bin/python3\", [\"python3\", \"dato /bin/systemctl /dev/watchdog0\"], 0) = 0";
    assert!(
        forbidden_attempts(clean).is_empty(),
        "ruta mencionada como dato no es ejecución"
    );
    let unit_alias = "execve(\"/bin/systemctl\", [\"systemctl\", \"set-property\"], 0) = 0";
    assert_eq!(forbidden_attempts(unit_alias), ["unit_change"]);
    let unit_dot = "execve(\"/usr/bin/../bin/systemctl\", [\"systemctl\"], 0) = 0";
    assert_eq!(forbidden_attempts(unit_dot), ["unit_change"]);
    let watchdog_dot = "openat(AT_FDCWD, \"/dev/./watchdog0\", O_RDONLY) = -1 ENOENT";
    assert_eq!(forbidden_attempts(watchdog_dot), ["watchdog"]);
    let watchdog_relative = "openat(3</dev>, \"watchdog\", O_RDONLY) = -1 ENOENT";
    assert_eq!(forbidden_attempts(watchdog_relative), ["watchdog"]);
    let watchdog_relative_dot = "openat(3</dev>, \"./watchdog0\", O_RDONLY) = -1 ENOENT";
    assert_eq!(forbidden_attempts(watchdog_relative_dot), ["watchdog"]);
    let argv_data = "execve(\"/usr/bin/echo\", [\"echo\", \"/dev/watchdog0\"], 0) = 0";
    assert!(
        forbidden_attempts(argv_data).is_empty(),
        "ruta en argv no es operando de syscall"
    );
    let execveat =
        "execveat(3</tmp/systemctl-witness>, \"\", [\"set-property\"], NULL, AT_EMPTY_PATH) = 0";
    assert_eq!(forbidden_attempts(execveat), ["unit_change"]);
    eprintln!("detector alias=3/3 watchdog_normalizado=3/3 execveat=1/1 argv_dato_limpio=0");
}

fn confinement_transition_checks() {
    assert_eq!(
        classify_pressures(SlicePressures {
            app: Some(50.0),
            docker: Some(0.0),
            system: Some(0.0),
        }),
        ConfinementClass::Confined
    );
    assert_eq!(
        classify_pressures(SlicePressures {
            app: Some(50.0),
            docker: Some(2.0),
            system: Some(0.0),
        }),
        ConfinementClass::General
    );
    assert_eq!(
        classify_pressures(SlicePressures {
            app: None,
            docker: Some(0.0),
            system: Some(0.0),
        }),
        ConfinementClass::Unknown
    );
    assert_eq!(
        confinement_decision(ConfinementMode::Off, ConfinementClass::Confined, 1, 40),
        ConfinementDecision::Retain
    );
    assert_eq!(
        confinement_decision(ConfinementMode::Observe, ConfinementClass::Confined, 1, 40),
        ConfinementDecision::WouldPet
    );
    assert_eq!(
        confinement_decision(ConfinementMode::Act, ConfinementClass::Confined, 1, 40),
        ConfinementDecision::PetInSimulation
    );
    assert_eq!(
        confinement_decision(ConfinementMode::Act, ConfinementClass::General, 1, 40),
        ConfinementDecision::Retain
    );
    assert_eq!(
        confinement_decision(ConfinementMode::Act, ConfinementClass::Confined, 41, 40),
        ConfinementDecision::Retain
    );
    compare_real_paso_confinado();
    compare_transition_path();
}

fn compare_real_paso_confinado() {
    const SOURCE: &str = r#"
import importlib.machinery, importlib.util, json, pathlib, sys
loader = importlib.machinery.SourceFileLoader('bb_usable_confinement', '/workspace/bin/bb-usable')
spec = importlib.util.spec_from_loader('bb_usable_confinement', loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
profiles = {
  'confinado': {'app':50.0, 'docker':0.0, 'system':0.0},
  'general': {'app':50.0, 'docker':2.0, 'system':0.0},
  'ilegible': {'app':None, 'docker':0.0, 'system':0.0},
}
rows = []
for name, pressure in profiles.items():
  for mode in ('off', 'observar', 'actuar'):
    for count in (0, 39, 40):
      module.modo_confinado = lambda mode=mode: mode
      module.presiones_slices = lambda pressure=pressure: pressure
      module._datos = lambda name=name, mode=mode, count=count: pathlib.Path(f'/tmp/paso-{name}-{mode}-{count}')
      module.diagnostico_atasco = lambda: {'synthetic': True}
      action, new_count = module.paso_confinado(count)
      if mode == 'off':
        clase = 'sin_consulta'
      else:
        record = pathlib.Path(f'/tmp/paso-{name}-{mode}-{count}/interruptores/atasco_confinado.jsonl')
        clase = json.loads(record.read_text().splitlines()[-1])['clase']
      rows.append([name, mode, count, clase, action, new_count])
print(json.dumps(rows, separators=(',', ':')))
"#;
    let output = Command::new("/usr/bin/python3")
        .args(["-B", "-I", "-c", SOURCE])
        .output()
        .unwrap_or_else(|error| instrument_failure(&format!("oráculo de confinamiento: {error}")));
    assert_output_success(&output, "decide_confinado verdadero");
    let expected: Vec<Vec<Value>> =
        serde_json::from_slice(&output.stdout)
            .unwrap_or_else(|error| instrument_failure(&format!("JSON de confinamiento: {error}")));
    let profiles = [
        (
            "confinado",
            SlicePressures {
                app: Some(50.0),
                docker: Some(0.0),
                system: Some(0.0),
            },
        ),
        (
            "general",
            SlicePressures {
                app: Some(50.0),
                docker: Some(2.0),
                system: Some(0.0),
            },
        ),
        (
            "ilegible",
            SlicePressures {
                app: None,
                docker: Some(0.0),
                system: Some(0.0),
            },
        ),
    ];
    let modes = [
        ("off", ConfinementMode::Off),
        ("observar", ConfinementMode::Observe),
        ("actuar", ConfinementMode::Act),
    ];
    let mut differences = Vec::new();
    for (profile_name, pressure) in profiles {
        for (mode_name, mode) in modes {
            for count in [0, 39, 40] {
                let (candidate, new_count, class) = step_confinement(mode, pressure, count, 40);
                let class_name = match (mode, class) {
                    (ConfinementMode::Off, _) => "sin_consulta",
                    (_, ConfinementClass::Confined) => "confinado",
                    (_, ConfinementClass::General) => "general",
                    (_, ConfinementClass::Unknown) => "sin_dato",
                };
                let candidate_name = decision_name(candidate);
                let oracle = expected
                    .iter()
                    .find(|row| row[0] == profile_name && row[1] == mode_name && row[2] == count)
                    .expect("fila del oráculo");
                if oracle[3] != class_name || oracle[4] != candidate_name || oracle[5] != new_count
                {
                    differences.push(format!(
                        "presiones={profile_name} modo={mode_name} previo={count}: main=({},{},{}) Rust=({class_name},{candidate_name},{new_count})",
                        oracle[3], oracle[4], oracle[5]
                    ));
                }
            }
        }
    }
    assert!(
        differences.is_empty(),
        "decisión confinada real vs Rust:\n{}",
        differences.join("\n")
    );
    eprintln!(
        "paso_confinado real: presiones sintéticas=3 modos=3 contadores previos=3 discrepancias=0"
    );
}

fn compare_transition_path() {
    let general = SlicePressures {
        app: Some(50.0),
        docker: Some(2.0),
        system: Some(0.0),
    };
    let confined = SlicePressures {
        app: Some(50.0),
        docker: Some(0.0),
        system: Some(0.0),
    };
    let mut inputs = vec![
        Input {
            psi: Some(50.0),
            probe: 0.001,
            mode: ConfinementMode::Off,
            pressures: general
        };
        41
    ];
    inputs.push(Input {
        psi: Some(50.0),
        probe: 0.001,
        mode: ConfinementMode::Act,
        pressures: confined,
    });
    inputs.extend(vec![
        Input {
            psi: Some(50.0),
            probe: 0.001,
            mode: ConfinementMode::Act,
            pressures: confined
        };
        39
    ]);
    inputs.push(Input {
        psi: Some(50.0),
        probe: 0.001,
        mode: ConfinementMode::Act,
        pressures: confined,
    });
    inputs.push(Input {
        psi: Some(50.0),
        probe: 0.001,
        mode: ConfinementMode::Act,
        pressures: general,
    });
    inputs.push(Input {
        psi: Some(50.0),
        probe: 0.001,
        mode: ConfinementMode::Act,
        pressures: confined,
    });
    inputs.push(Input {
        psi: Some(50.0),
        probe: 0.001,
        mode: ConfinementMode::Off,
        pressures: confined,
    });
    inputs.push(Input {
        psi: Some(50.0),
        probe: 0.001,
        mode: ConfinementMode::Act,
        pressures: confined,
    });
    let oracle = events_by_step(&oracle_events("transicion", &inputs));
    assert_eq!(
        oracle.len(),
        inputs.len(),
        "main real ejecutó todos los pasos de transición"
    );
    let mut state = State::default();
    let mut transitions = Vec::new();
    for (index, (events, input)) in oracle.iter().zip(inputs).enumerate() {
        let result = step(
            &mut state,
            Sample {
                psi_full_avg10: input.psi,
                probe_seconds: input.probe,
                confinement_mode: input.mode,
                pressures: input.pressures,
            },
        );
        let actual = events.iter().find(|event| event[0] == "confinado_result");
        let actual_count = actual
            .and_then(|event| event[1].as_u64())
            .map(|count| count as usize);
        let actual_action = actual.and_then(|event| event[2].as_str());
        let expected_pet = expected_pet(events);
        assert_eq!(
            result.simulated_watchdog_notification,
            expected_pet,
            "notify paso {}",
            index + 1
        );
        if let Some(count) = actual_count {
            assert_eq!(
                result.confined_steps,
                count,
                "contador confinado paso {}",
                index + 1
            );
            assert_eq!(
                result.confinement_decision.map(decision_name),
                actual_action,
                "acción paso {}",
                index + 1
            );
        }
        transitions.push(result.confined_steps);
    }
    assert_eq!(transitions[40], 0, "off/general retiene contador en cero");
    assert_eq!(transitions[41], 1, "primera confinada arranca en uno");
    assert_eq!(transitions[80], 40, "racha confinada llega al tope");
    assert_eq!(transitions[81], 41, "paso 41 cruza el tope");
    assert_eq!(transitions[82], 0, "salir a general reinicia");
    assert_eq!(transitions[83], 1, "volver a confinada reanuda en uno");
    assert_eq!(transitions[84], 0, "volver a off reinicia");
    assert_eq!(transitions[85], 1, "regresar a actuar reinicia en uno");
    eprintln!(
        "main+paso_confinado transición: 41 off/general; 1->40 pet simulado; 41 retiene; general=0; confinada=1; off=0; actuar=1"
    );
}

fn isolation_error(parent_pid_ns: &str, parent_net_ns: &str) -> Result<(), String> {
    let pid_ns = fs::read_link("/proc/self/ns/pid").map_err(|error| error.to_string())?;
    let net_ns = fs::read_link("/proc/self/ns/net").map_err(|error| error.to_string())?;
    if pid_ns.to_string_lossy() == parent_pid_ns || net_ns.to_string_lossy() == parent_net_ns {
        return Err(format!("namespace unchanged pid={pid_ns:?} net={net_ns:?}"));
    }
    for path in [
        "/dev/watchdog",
        "/dev/watchdog0",
        "/run/systemd/private",
        "/run/dbus/system_bus_socket",
        "/run/systemd/notify",
    ] {
        if Path::new(path).exists() {
            return Err(format!("host actuator/socket path visible: {path}"));
        }
    }
    if std::env::var_os("NOTIFY_SOCKET").is_some() {
        return Err("NOTIFY_SOCKET heredado".to_owned());
    }
    Ok(())
}

fn forbidden_attempts(trace: &str) -> Vec<&'static str> {
    let mut found = Vec::new();
    let lines = trace.lines().collect::<Vec<_>>();
    if lines.iter().any(|line| {
        [
            "kill(",
            "tkill(",
            "tgkill(",
            "pidfd_send_signal(",
            "killpg(",
        ]
        .iter()
        .any(|call| line.contains(call))
    }) {
        found.push("signal");
    }
    let watchdog_access = lines.iter().any(|line| {
        ["open(", "openat(", "openat2("].iter().any(|call| {
            let Some(path) = syscall_first_path(line, call) else {
                return false;
            };
            let resolved = resolve_trace_path(line, call, path);
            resolved == "/dev/watchdog" || resolved == "/dev/watchdog0"
        })
    });
    if watchdog_access {
        found.push("watchdog");
    }
    let socket_access = lines.iter().any(|line| {
        ["connect(", "sendto(", "sendmsg("].iter().any(|call| {
            syscall_first_path(line, call).is_some_and(|path| {
                let resolved = normalize_path(path);
                resolved == "/run/systemd/private" || resolved == "/run/dbus/system_bus_socket"
            })
        })
    });
    if socket_access || trace.contains("NOTIFY_SOCKET") {
        found.push("systemd_socket");
    }
    let unit_exec = lines.iter().any(|line| {
        if line.contains("execveat(") {
            return true;
        }
        let Some(path) = syscall_first_path(line, "execve(") else {
            return false;
        };
        let normalized = normalize_path(path);
        Path::new(&normalized)
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name == "systemctl" || name == "systemctl-witness")
    });
    if unit_exec {
        found.push("unit_change");
    }
    found
}

fn resolve_trace_path(line: &str, call: &str, path: &str) -> String {
    let normalized = normalize_path(path);
    if path.starts_with('/') || call == "open(" {
        return normalized;
    }
    let Some(args) = line.get(line.find(call).unwrap_or(0) + call.len()..) else {
        return normalized;
    };
    let dirfd = args.split(',').next().unwrap_or("");
    let base = dirfd
        .split_once("</")
        .and_then(|(_, tail)| tail.split_once('>').map(|(p, _)| format!("/{p}")));
    match base {
        Some(base) => normalize_path(&format!("{base}/{path}")),
        None => normalized,
    }
}

fn syscall_first_path<'a>(line: &'a str, call: &str) -> Option<&'a str> {
    let rest = line.get(line.find(call)? + call.len()..)?;
    rest.get(rest.find('"')? + 1..)?.split('"').next()
}

fn normalize_path(path: &str) -> String {
    let mut components = Vec::new();
    for component in Path::new(path).components() {
        match component {
            std::path::Component::RootDir => components.clear(),
            std::path::Component::CurDir => {}
            std::path::Component::ParentDir => {
                components.pop();
            }
            std::path::Component::Normal(part) => {
                components.push(part.to_string_lossy().into_owned())
            }
            std::path::Component::Prefix(_) => return path.to_owned(),
        }
    }
    format!("/{}", components.join("/"))
}

fn sandbox_run(mode: &str, pid_ns: &str, net_ns: &str, evidence: &Path, tmp: &Path) -> Output {
    let executable = std::env::current_exe().expect("test executable");
    let repository = env!("CARGO_MANIFEST_DIR");
    let trace_name = format!(
        "{mode}-{}.trace",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("reloj posterior a epoch")
            .as_nanos()
    );
    let trace_path = format!("/evidence/{trace_name}");
    let mut command = Command::new("/usr/bin/bwrap");
    command.args([
        "--clearenv",
        "--unshare-all",
        "--die-with-parent",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/lib",
        "/lib",
        "--symlink",
        "usr/bin",
        "/bin",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/run",
        "--dir",
        "/candidate",
        "--dir",
        "/evidence",
        "--ro-bind",
        repository,
        "/workspace",
        "--ro-bind",
        executable.to_str().expect("ruta UTF-8 del test"),
        "/candidate/usable-paridad-test",
        "--bind",
    ]);
    command
        .arg(evidence)
        .arg("/evidence")
        .args(["--bind"])
        .arg(tmp)
        .args([
            "/tmp",
            "--chdir",
            "/workspace",
            "--setenv",
            "PATH",
            "/usr/bin:/bin",
            "--setenv",
            "HOME",
            "/tmp",
            "--setenv",
            "TMPDIR",
            "/tmp",
            "--setenv",
            "BB_RUN_MODE",
            mode,
            "--setenv",
            "BB_ORACLE_PATH",
            if mode == "oracle-failure" {
                "/workspace/bin/bb-usable-instrument-missing"
            } else {
                "/workspace/bin/bb-usable"
            },
            "--setenv",
            "BB_PARENT_PID_NS",
            pid_ns,
            "--setenv",
            "BB_PARENT_NET_NS",
            net_ns,
            "--setenv",
            "BB_TRACE_NAME",
            &trace_name,
            "/usr/bin/strace",
            "-f",
            "-qq",
            "-yy",
            "-s",
            "256",
            "-e",
            "trace=kill,tkill,tgkill,pidfd_send_signal,connect,sendto,sendmsg,open,openat,openat2,execve,execveat",
            "-o",
            &trace_path,
            "/candidate/usable-paridad-test",
            "--exact",
            "isolated_worker",
            "--ignored",
            "--nocapture",
        ]);
    command
        .output()
        .expect("bwrap privado y strace disponibles")
}

fn classify_worker_failure(isolation_ok: bool, exit_code: Option<i32>) -> &'static str {
    match (isolation_ok, exit_code) {
        (true, Some(86)) => "COULD_NOT_RUN",
        (true, _) => "FAIL",
        (false, _) => "COULD_NOT_RUN",
    }
}

#[test]
fn worker_protocol_separates_instrument_failure_from_subject_failure() {
    assert_eq!(classify_worker_failure(true, Some(86)), "COULD_NOT_RUN");
    assert_eq!(classify_worker_failure(true, Some(101)), "FAIL");
    assert_eq!(classify_worker_failure(false, Some(101)), "COULD_NOT_RUN");
}

#[test]
fn close_check_runs_subject_and_negative_in_private_bwrap() {
    let evidence = PathBuf::from(std::env::var("BB_USABLE_EVIDENCE").expect(
        "BB_USABLE_EVIDENCE debe apuntar a tasks/evidence/BB-RUST-USABLE-PARIDAD-01/ejecucion",
    ));
    let tmp = std::env::var("BB_USABLE_TMP").expect("BB_USABLE_TMP dentro del scratch privado");
    fs::create_dir_all(&evidence).expect("directorio de evidencia autorizado");
    fs::create_dir_all(&tmp).expect("tmp privado");
    let pid_ns = fs::read_link("/proc/self/ns/pid").expect("pid namespace padre");
    let net_ns = fs::read_link("/proc/self/ns/net").expect("network namespace padre");
    let pid_ns = pid_ns.to_string_lossy().into_owned();
    let net_ns = net_ns.to_string_lossy().into_owned();

    for mode in ["subject", "adverse", "oracle-failure"] {
        let temp_run = Path::new(&tmp).join(format!(
            "{mode}-{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("reloj posterior a epoch")
                .as_nanos()
        ));
        fs::create_dir_all(&temp_run).expect("tmp privado desde scratch propio");
        let output = sandbox_run(mode, &pid_ns, &net_ns, &evidence, &temp_run);
        if mode == "oracle-failure" {
            let protocol_stdout = String::from_utf8_lossy(&output.stdout).into_owned();
            let protocol_stderr = String::from_utf8_lossy(&output.stderr).into_owned();
            fs::write(evidence.join("oracle-failure.stdout"), &output.stdout)
                .expect("salida del oráculo fallido preservada");
            fs::write(evidence.join("oracle-failure.stderr"), &output.stderr)
                .expect("diagnóstico del oráculo fallido preservado");
            let protocol_lines = protocol_stdout
                .lines()
                .chain(protocol_stderr.lines())
                .map(str::to_owned)
                .collect::<Vec<_>>();
            assert!(protocol_lines.iter().any(|line| line == "ISOLATION_OK mode=oracle-failure"));
            assert!(protocol_lines.iter().any(|line| line.starts_with("WORKER_STATUS=COULD_NOT_RUN:")));
            assert!(
                protocol_stdout.contains("FileNotFoundError")
                    || protocol_stderr.contains("FileNotFoundError"),
                "la ruta de oráculo ausente debe producir FileNotFoundError observable"
            );
            assert_eq!(
                classify_worker_failure(true, output.status.code()),
                "COULD_NOT_RUN",
                "el fallo sintético del oráculo debe conservar su categoría técnica"
            );
            assert_eq!(output.status.code(), Some(86));
            eprintln!("sandbox=oracle-failure classification=COULD_NOT_RUN rc=86");
            continue;
        }
        if !output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            let isolation_ok = stdout
                .lines()
                .chain(stderr.lines())
                .any(|line| line.starts_with("ISOLATION_OK mode="));
            let disposition = classify_worker_failure(isolation_ok, output.status.code());
            panic!(
                "{disposition}: bwrap/strace {mode}: rc={:?}, stdout={}, stderr={}",
                output.status.code(),
                stdout,
                stderr
            );
        }
        let combined = format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        let trace_name = combined
            .lines()
            .find_map(|line| line.strip_prefix("TRACE_FILE="))
            .unwrap_or_else(|| panic!("COULD_NOT_RUN: worker sin nombre de traza: {combined}"));
        fs::write(
            evidence.join(format!("{trace_name}.stdout")),
            &output.stdout,
        )
        .expect("salida de worker preservada");
        fs::write(
            evidence.join(format!("{trace_name}.stderr")),
            &output.stderr,
        )
        .expect("diagnóstico de worker preservado");
        let trace = fs::read_to_string(evidence.join(trace_name)).unwrap_or_else(|error| {
            panic!("COULD_NOT_RUN: traza strace ilegible: {error}")
        });
        let attempts = forbidden_attempts(&trace);
        if mode == "subject" {
            assert!(
                attempts.is_empty(),
                "sujeto intentó efectos prohibidos: {attempts:?}"
            );
        } else {
            assert_eq!(
                attempts,
                ["signal", "watchdog", "systemd_socket", "unit_change"]
            );
            assert!(
                trace
                    .lines()
                    .any(|line| line.contains("kill(2147483647, 0)") && line.contains("ESRCH")),
                "señal sintética no falló como esperado"
            );
            assert!(
                trace
                    .lines()
                    .any(|line| line.contains("tkill(") && line.contains("ESRCH")),
                "tkill no falló como esperado"
            );
            assert!(
                trace
                    .lines()
                    .any(|line| line.contains("tgkill(") && line.contains("ESRCH")),
                "tgkill no falló como esperado"
            );
            assert!(
                trace
                    .lines()
                    .any(|line| line.contains("pidfd_send_signal(") && line.contains("EBADF")),
                "pidfd_send_signal no falló como esperado"
            );
            assert!(
                trace
                    .lines()
                    .any(|line| line.contains("/dev/watchdog") && line.contains("ENOENT")),
                "watchdog sintético no inaccesible"
            );
            assert!(
                trace.lines().any(|line| line.contains("openat2(")
                    && line.contains("/dev/watchdog")
                    && line.contains("ENOENT")),
                "openat2 de watchdog no inaccesible"
            );
            assert!(
                trace.lines().any(|line| line.contains("openat(")
                    && line.contains("</dev>")
                    && line.contains("\"watchdog\"")
                    && line.contains("ENOENT")),
                "openat relativo no detectado"
            );
            assert!(
                trace.lines().any(|line| line.contains("openat2(")
                    && line.contains("</dev>")
                    && line.contains("\"watchdog\"")
                    && line.contains("ENOENT")),
                "openat2 relativo no detectado"
            );
            assert!(
                trace
                    .lines()
                    .any(|line| line.contains("/run/systemd/private") && line.contains("ENOENT")),
                "socket systemd sintético no inaccesible"
            );
            assert!(
                trace
                    .lines()
                    .any(|line| line.contains("execveat(") && line.contains("systemctl-witness")),
                "ejecución sintética execveat no observada"
            );
            assert!(
                trace.contains("\"bb-rust-paridad-synthetic.service\"")
                    && trace.contains("\"MemoryMax=1G\""),
                "argv sintético de cambio de unidad no quedó en traza"
            );
        }
        eprintln!(
            "sandbox={mode} pid_ns_privado net_ns_privado forbidden_attempts={:?}",
            attempts
        );
    }
    fs::write(
        evidence.join("sandbox-summary.txt"),
        "subject: rc=0 forbidden_attempts=0\nadverse: rc=0 blocked_attempts=4/4\nsynthetic_oracle_failure: rc=86 classification=COULD_NOT_RUN\nsubject_adverse_could_not_run=0\n",
    )
    .expect("resumen de barrera y control negativo");
}

#[test]
#[ignore = "worker sólo corre por close_check dentro de bwrap"]
fn isolated_worker() {
    let Some(mode) = std::env::var_os("BB_RUN_MODE") else {
        return;
    };
    let parent_pid_ns = std::env::var("BB_PARENT_PID_NS").unwrap_or_default();
    let parent_net_ns = std::env::var("BB_PARENT_NET_NS").unwrap_or_default();
    if let Err(error) = isolation_error(&parent_pid_ns, &parent_net_ns) {
        panic!("COULD_NOT_RUN: barrera de aislamiento: {error}");
    }
    println!("ISOLATION_OK mode={}", mode.to_string_lossy());
    println!(
        "TRACE_FILE={}",
        std::env::var("BB_TRACE_NAME").expect("nombre único de traza")
    );
    match mode.to_string_lossy().as_ref() {
        "subject" => {
            detector_alias_controls();
            confinement_transition_checks();
            compare_scenarios();
        }
        "adverse" => run_synthetic_adversary(),
        "oracle-failure" => {
            let _ = oracle_events("fallo_oraculo_ausente", &[sample(Some(50.0))]);
        }
        _ => panic!("COULD_NOT_RUN: modo de worker desconocido"),
    }
}

fn instrument_failure(message: &str) -> ! {
    if std::env::var_os("BB_RUN_MODE").is_some() {
        eprintln!("WORKER_STATUS=COULD_NOT_RUN: {message}");
        std::process::exit(86)
    }
    panic!("COULD_NOT_RUN: {message}")
}

fn run_synthetic_adversary() {
    let witness = Path::new("/tmp/systemctl-witness");
    fs::write(
        witness,
        "#!/usr/bin/python3 -BI\nimport socket\ns=socket.socket(socket.AF_UNIX)\ntry: s.connect('/run/systemd/private')\nexcept OSError: pass\n",
    )
    .expect("testigo de sistema sintético en tmpfs privado");
    fs::set_permissions(witness, fs::Permissions::from_mode(0o755)).expect("testigo ejecutable");

    let invalid_pid = 2_147_483_647 as libc::pid_t;
    for (name, result) in [
        ("tkill", unsafe {
            libc::syscall(libc::SYS_tkill, invalid_pid, 0)
        }),
        ("tgkill", unsafe {
            libc::syscall(libc::SYS_tgkill, invalid_pid, invalid_pid, 0)
        }),
        ("pidfd_send_signal", unsafe {
            libc::syscall(
                libc::SYS_pidfd_send_signal,
                -1 as libc::c_int,
                0 as libc::c_int,
                std::ptr::null::<libc::siginfo_t>(),
                0 as libc::c_uint,
            )
        }),
    ] {
        assert_eq!(result, -1, "syscall sintética {name} debía fallar");
    }
    let watchdog = CString::new("/dev/watchdog").expect("ruta sin NUL");
    assert_eq!(
        unsafe { libc::open(watchdog.as_ptr(), libc::O_RDONLY) },
        -1,
        "open sintético de watchdog debía fallar"
    );
    #[repr(C)]
    struct OpenHow {
        flags: u64,
        mode: u64,
        resolve: u64,
    }
    let how = OpenHow {
        flags: libc::O_RDONLY as u64,
        mode: 0,
        resolve: 0,
    };
    assert_eq!(
        unsafe {
            libc::syscall(
                libc::SYS_openat2,
                libc::AT_FDCWD,
                watchdog.as_ptr(),
                &how,
                std::mem::size_of::<OpenHow>(),
            )
        },
        -1,
        "openat2 sintético de watchdog debía fallar"
    );
    let dev_dir = CString::new("/dev").expect("ruta sin NUL");
    let dev_fd = unsafe { libc::open(dev_dir.as_ptr(), libc::O_PATH | libc::O_DIRECTORY) };
    assert!(dev_fd >= 0, "directorio /dev privado accesible");
    let relative_watchdog = CString::new("watchdog").expect("ruta sin NUL");
    assert_eq!(
        unsafe { libc::openat(dev_fd, relative_watchdog.as_ptr(), libc::O_RDONLY) },
        -1,
        "openat relativo sintético de watchdog debía fallar"
    );
    assert_eq!(
        unsafe {
            libc::syscall(
                libc::SYS_openat2,
                dev_fd,
                relative_watchdog.as_ptr(),
                &how,
                std::mem::size_of::<OpenHow>(),
            )
        },
        -1,
        "openat2 relativo sintético de watchdog debía fallar"
    );
    unsafe { libc::close(dev_fd) };
    let child = unsafe { libc::fork() };
    assert!(child >= 0, "fork de testigo sintético");
    if child == 0 {
        let path = CString::new("/tmp/systemctl-witness").expect("ruta sin NUL");
        let empty = CString::new("").expect("ruta vacía");
        let args = [
            CString::new("systemctl-witness").unwrap(),
            CString::new("set-property").unwrap(),
            CString::new("bb-rust-paridad-synthetic.service").unwrap(),
            CString::new("MemoryMax=1G").unwrap(),
        ];
        let mut argv = args.iter().map(|arg| arg.as_ptr()).collect::<Vec<_>>();
        argv.push(std::ptr::null());
        let envp: [*const libc::c_char; 1] = [std::ptr::null()];
        let fd = unsafe { libc::open(path.as_ptr(), libc::O_PATH) };
        if fd >= 0 {
            unsafe {
                libc::syscall(
                    libc::SYS_execveat,
                    fd,
                    empty.as_ptr(),
                    argv.as_ptr(),
                    envp.as_ptr(),
                    libc::AT_EMPTY_PATH,
                );
            }
        }
        unsafe { libc::_exit(127) };
    }
    let mut status = 0;
    assert_eq!(unsafe { libc::waitpid(child, &mut status, 0) }, child);
    assert!(
        libc::WIFEXITED(status) && libc::WEXITSTATUS(status) == 0,
        "execveat testigo sintético status={status}"
    );

    let code = r#"
import os, socket, subprocess
for probe in (
    lambda: os.kill(2147483647, 0),
    lambda: os.open('/dev/watchdog', os.O_RDONLY),
    lambda: socket.socket(socket.AF_UNIX).connect('/run/systemd/private'),
):
    try: probe()
    except (OSError, subprocess.CalledProcessError): pass
    else: raise RuntimeError('negative control unexpectedly succeeded')
subprocess.run(['/tmp/systemctl-witness', 'set-property', 'bb-rust-paridad-synthetic.service', 'MemoryMax=1G'], check=True)
"#;
    let output = Command::new("/usr/bin/python3")
        .args(["-B", "-I", "-c", code])
        .output()
        .unwrap_or_else(|error| instrument_failure(&format!("Python stdlib: {error}")));
    assert_output_success(&output, "testigo adverso sintético");
}

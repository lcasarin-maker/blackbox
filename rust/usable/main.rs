#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConfinementMode {
    Off,
    Observe,
    Act,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConfinementClass {
    General,
    Confined,
    Unknown,
}

#[derive(Clone, Copy, Debug)]
pub struct SlicePressures {
    pub app: Option<f64>,
    pub docker: Option<f64>,
    pub system: Option<f64>,
}

pub fn classify_pressures(pressures: SlicePressures) -> ConfinementClass {
    const PSI_THRESHOLD: f64 = 10.0;
    const OTHER_SLICES_MAX: f64 = 1.0;
    let (Some(app), Some(docker), Some(system)) =
        (pressures.app, pressures.docker, pressures.system)
    else {
        return ConfinementClass::Unknown;
    };
    if app >= PSI_THRESHOLD && docker <= OTHER_SLICES_MAX && system <= OTHER_SLICES_MAX {
        ConfinementClass::Confined
    } else {
        ConfinementClass::General
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConfinementDecision {
    Retain,
    WouldPet,
    PetInSimulation,
}

pub fn confinement_decision(
    mode: ConfinementMode,
    class: ConfinementClass,
    consecutive: usize,
    maximum: usize,
) -> ConfinementDecision {
    if mode == ConfinementMode::Off || class != ConfinementClass::Confined || consecutive > maximum
    {
        ConfinementDecision::Retain
    } else if mode == ConfinementMode::Observe {
        ConfinementDecision::WouldPet
    } else {
        // This is a recorded hypothetical notification only; this module has no actuator.
        ConfinementDecision::PetInSimulation
    }
}

pub fn step_confinement(
    mode: ConfinementMode,
    pressures: SlicePressures,
    previous: usize,
    maximum: usize,
) -> (ConfinementDecision, usize, ConfinementClass) {
    if mode == ConfinementMode::Off {
        return (ConfinementDecision::Retain, 0, ConfinementClass::Unknown);
    }
    let class = classify_pressures(pressures);
    let consecutive = if class == ConfinementClass::Confined {
        previous + 1
    } else {
        0
    };
    (
        confinement_decision(mode, class, consecutive, maximum),
        consecutive,
        class,
    )
}

#[derive(Clone, Copy, Debug)]
pub struct Sample {
    pub psi_full_avg10: Option<f64>,
    pub probe_seconds: f64,
    pub confinement_mode: ConfinementMode,
    pub pressures: SlicePressures,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Outcome {
    Healthy,
    HighPsi,
    LowPsiRetainsStreak,
    Recovery,
    UnreadablePsi,
    Collapse,
    ConfinedObserve,
    ConfinedActHypothetical,
    LateProbe,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StepResult {
    pub outcome: Outcome,
    pub simulated_watchdog_notification: bool,
    pub sustained_high: usize,
    pub consecutive_lows: usize,
    pub confined_steps: usize,
    pub confinement_decision: Option<ConfinementDecision>,
}

#[derive(Clone, Copy, Debug, Default)]
pub struct State {
    sustained_high: usize,
    consecutive_lows: usize,
    confined_steps: usize,
}

pub fn step(state: &mut State, sample: Sample) -> StepResult {
    const PSI_THRESHOLD: f64 = 10.0;
    const SUSTAINED_SAMPLES: usize = 10;
    const LOWS_TO_RECOVER: usize = 2;
    const PROBE_DEADLINE_SECONDS: f64 = 300.0;

    let outcome;
    let mut notify = false;
    let mut confinement_decision = None;
    if sample.probe_seconds > PROBE_DEADLINE_SECONDS {
        outcome = Outcome::LateProbe;
    } else {
        match sample.psi_full_avg10 {
            None => {
                outcome = Outcome::UnreadablePsi;
                notify = state.sustained_high < SUSTAINED_SAMPLES;
            }
            Some(psi) if psi >= PSI_THRESHOLD => {
                state.sustained_high += 1;
                state.consecutive_lows = 0;
                if state.sustained_high < SUSTAINED_SAMPLES {
                    outcome = Outcome::HighPsi;
                    notify = true;
                } else {
                    let (decision, confined_steps, _class) = step_confinement(
                        sample.confinement_mode,
                        sample.pressures,
                        state.confined_steps,
                        40,
                    );
                    state.confined_steps = confined_steps;
                    confinement_decision = Some(decision);
                    match decision {
                        ConfinementDecision::Retain => outcome = Outcome::Collapse,
                        ConfinementDecision::WouldPet => outcome = Outcome::ConfinedObserve,
                        ConfinementDecision::PetInSimulation => {
                            outcome = Outcome::ConfinedActHypothetical;
                            notify = true;
                        }
                    }
                }
            }
            Some(_) => {
                state.consecutive_lows += 1;
                if state.consecutive_lows >= LOWS_TO_RECOVER {
                    let recovering_streak = state.sustained_high > 0;
                    state.sustained_high = 0;
                    state.consecutive_lows = 0;
                    state.confined_steps = 0;
                    outcome = if recovering_streak {
                        Outcome::Recovery
                    } else {
                        Outcome::Healthy
                    };
                } else if state.sustained_high > 0 {
                    outcome = Outcome::LowPsiRetainsStreak;
                } else {
                    outcome = Outcome::Healthy;
                }
                notify = state.sustained_high < SUSTAINED_SAMPLES;
            }
        }
    }
    StepResult {
        outcome,
        simulated_watchdog_notification: notify,
        sustained_high: state.sustained_high,
        consecutive_lows: state.consecutive_lows,
        confined_steps: state.confined_steps,
        confinement_decision,
    }
}

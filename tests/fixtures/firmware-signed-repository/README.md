# Signed repository parser fixture

This is a byte-for-byte copy of the read-only NVIDIA Base OS `noble-updates/dgx` APT metadata and keyring present in the development environment on 2026-10-04. It contains a signed InRelease, its exact Packages index, and the repository keyring. The source package metadata identifies `nvidia-spark-mlnx-firmware-manager` 5.0.8-1; the captured maintainer-script, device, and package-command rows in the test remain synthetic parser fixtures and do not represent that package's actual archive contents.

The repository signature was verified with `tools.apt_sources.verify_release_signature` against the exact archived files. InRelease SHA-256: `4d6eee611a64df4275a70d16b030813b0e13d98a248955ee18fa80ea33173d81`. Packages SHA-256: `54e4c3d2033bffe7179adeccfaad8442c208b9bffa816972806c2dea317a224e`. Keyring SHA-256: `5fb5c807c302b5ff490d0a48581dfb270ff8fb0742e44931529f86168e8e6478`. Signing fingerprint: `5E62373C3E8236A0D1123818208CE844D9F220AD`.

The test supplies a synthetic plan anchor solely to exercise parser behavior. It does not authorize a firmware operation or authenticate any live host capture.

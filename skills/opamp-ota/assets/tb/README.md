# OpAmp & OTA Process-Independent Spectre Testbench Suites

Self-contained Spectre testbench suites for single-ended and fully differential operational amplifiers and OTAs, backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`single_ended/`](single_ended/README.md) | `tb_ota_stb_ac.scs`, `tb_ota_cmrr_psrr_noise.scs`, `tb_ota_slew_settle.scs`, `analyze_ota.py` | `iprobe` loop `stb` (`A0`, `UGF`, `PM`, `GM`), 4-replica DC-servo CMRR / PSRR+ / PSRR- / input-referred noise, large-signal slew rate (`SR+`/`SR-`) & `0.1%` settling |
| [`fully_diff/`](fully_diff/README.md) | `tb_fd_ota_dm_cm_stb.scs`, `tb_fd_ota_slew_settle.scs`, `analyze_fd_ota.py` | Standalone lossless reciprocal Tian balun (`diff_stb_probe`) simultaneous differential-mode & CMFB `stb`, differential slew/settling & CM kick |

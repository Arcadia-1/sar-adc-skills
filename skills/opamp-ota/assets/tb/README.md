# OpAmp & OTA Process-Independent Spectre X Testbench Suites

Self-contained **Spectre X (`+preset=cx`)** signoff testbench suites for single-ended and fully differential operational amplifiers and OTAs (16 decks covering 29 industrial characterization items), backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`single_ended/`](single_ended/README.md) | 8 `.scs` decks (`tb_ota_stb_ac`, `tb_ota_cmrr_psrr_noise`, `tb_ota_dc_signoff`, `tb_ota_cl_zout_gm`, `tb_ota_slew_settle`, `tb_ota_thd_fpbw`, `tb_ota_power_ramp`, `tb_ota_supply_surge_cmstep`) + `analyze_ota.py` | `iprobe` loop `stb`, 5-replica CMRR/4R-bridge/PSRR±/noise, offset/tempco/multi-method ICMR/swing-vs-$R_L$/VIDR/$V_{\text{DD}}$ range, closed-loop AC/group-delay/$Z_{\text{out}}$/$Z_{\text{in}}$/OTA $g_m$, slew/settling, coherent THD/HD2/HD3/$\text{BW}_{\text{full}}$, power-ramp & supply-surge/CM-step |
| [`fully_diff/`](fully_diff/README.md) | 8 `.scs` decks (`tb_fd_ota_dm_cm_stb`, `tb_fd_ota_cmrr_psrr_noise`, `tb_fd_ota_dc_signoff`, `tb_fd_ota_cl_zout_gm`, `tb_fd_ota_slew_settle`, `tb_fd_ota_thd_fpbw`, `tb_fd_ota_power_ramp`, `tb_fd_ota_supply_surge_cmstep`) + `analyze_fd_ota.py` | Lossless Tian balun DM+CM `stb`, FD CM→CM/CM→DM/PSRR±/diff noise, DM offset & $V_{\text{OCM}}$ drift/ICMR/diff swing-vs-$R_L$/VIDR, closed-loop AC/$Z_{\text{out,DM}}$/$Z_{\text{out,CM}}$/OTA $g_m$, diff slew/settling, coherent THD/HD2/HD3/$\text{BW}_{\text{full}}$, power-ramp & supply-surge/CM-step |

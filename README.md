# PulseDuct — ElbowOS

Neon pipe-dream arcade written in **Python 3 + pygame**.

Rotate conduit tiles so magenta plasma can run from the source well to the sink.
Featured account: [x.com/ElbowOS](https://x.com/ElbowOS)

## Play

```bash
pip install -r requirements.txt
python3 pulseduct.py
```

- Arrow keys move the highlight
- Space / Enter / click rotates a tile
- Esc quits

## Record a 9:16 reel

```bash
RECORD=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 pulseduct.py
```

Writes `PulseDuct_ElbowOS.mp4` (1080×1920, 15s, 30fps, H.264).

## Links

- Reel on Drive: https://drive.google.com/file/d/1edU_Mbm1mRzkqtUmsgMOTPd_vf1RFjlO/view
- https://x.com/ElbowOS

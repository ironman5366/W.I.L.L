[Unit]
Description=Telegram interface for W.I.L.L
After=network-online.target

[Service]
Type=idle
WorkingDirectory=/usr/local/W.I.L.L/interfaces/W.I.L.L-Telegram
Restart=always
ExecStart=/usr/bin/python3 /usr/local/W.I.L.L/interfaces/W.I.L.L-Telegram/main.py
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target

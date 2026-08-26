# Beat 3c: failure handling on camera. One poisoned message retries five times
# and lands in the dead-letter queue, while the other six transactions continue.
Output video/build/shots/dlq.mp4
Set Theme "Catppuccin Mocha"
Set FontSize 16
Set Width 1800
Set Height 620
Set Padding 30
Set TypingSpeed 45ms

Type "python3 -m grantloop.replay --dlq TXN-004 --plain | tail -20"
Sleep 700ms
Enter
Sleep 9s

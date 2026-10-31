EYE3 Box kit: install EYE3 once, from a USB stick or the network
================================================================

What it is
  A small program (EYE3 Link) plus a start-up script. After one install, the computer that is plugged
  into your TV with HDMI starts EYE3 by itself at every power-on, shows EYE3 Home fullscreen, keeps
  EYE3 Link running, fixes connection problems by itself and updates itself.

What it needs
  A PC, laptop, mini-PC, Raspberry Pi or Mac connected to the TV by HDMI.
  The TV itself (for example a Philips Saphi) cannot install software from a USB stick. A TV only plays
  what a box behind it sends.

Install from a USB stick (no internet needed for the program)
  Windows : open the folder on the stick and double-click  install.bat
  Linux / Raspberry Pi / Mac : open a terminal in the folder and run   sh install.sh
  Your own playlists: copy .m3u / .m3u8 / .txt files into the  playlists  folder on the stick before you
  install, or into  EYE3\playlists  afterwards.

Install over the network (no stick)
  Download the kit for your system from
    https://github.com/j-janko420/EYE3-VISION/releases/tag/eye3-link-latest
  unzip it and run install.bat / install.sh. If the program is missing from the folder, the installer
  downloads it and checks its SHA-256 against the published list before it installs anything.

Try first without changing anything
  sh install.sh --dry-run          (Windows: install.bat -DryRun)

What runs on its own afterwards
  * EYE3 Link starts at every sign-in and is restarted after a crash.
  * Updates: EYE3 Link looks for a new version, downloads it, checks the SHA-256, and swaps it in at the
    next start (it waits until nothing is playing).
  * Fixes: if the computer cannot find a provider's address, the agent asks a secure DNS service. It is
    not a VPN. EYE3 does not include a VPN.
  * EYE3 Home (the page) reconnects by itself when EYE3 Link restarts. Tap the "Agent" chip on the
    top bar to see what the agent did.

Your own lists, the Explicit section
  EYE3 ships no channels. Only your own accounts and your own files are shown. Adult groups from your
  own files stay hidden until you unlock the Explicit section (double-click the eye logo, or Shift+X,
  tick "I am 18 or older", optional PIN). They are never shown in the normal lists.

Remove
  sh install.sh --uninstall    (Windows: install.bat -Uninstall)   removes the start-up entries only.

Chrome may ask once to allow EYE3 Home to talk to apps on this computer. Choose Allow.

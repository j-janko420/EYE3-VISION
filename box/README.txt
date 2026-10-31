EYE3 Box kit: install EYE3 once, from a USB stick or the network
================================================================

What it is
  A small program (EYE3 Link) plus a start-up script. After one install, EYE3 Link starts by itself at
  every sign-in, keeps running, fixes connection problems by itself and updates itself.
  By default your normal browser is NOT touched: your saved lists, accounts, PIN and theme stay as they are,
  and you open EYE3 Home from the "EYE3 Home" link the installer puts on your Desktop.
  For the box behind a TV, add the kiosk option and EYE3 Home also opens fullscreen at every start.

What it needs
  A PC, laptop, mini-PC, Raspberry Pi or Mac connected to the TV by HDMI.
  The TV itself (for example a Philips Saphi) cannot install software from a USB stick. A TV only plays
  what a box behind it sends.

Install from a USB stick (no internet needed for the program)
  Windows : open the folder on the stick and double-click  install.bat
            (box behind a TV: run  install.bat -Kiosk  from a command prompt)
  Linux / Raspberry Pi / Mac : open a terminal in the folder and run   sh install.sh
            (box behind a TV:  sh install.sh --kiosk)
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

Remove / go back to normal
  sh install.sh --uninstall    (Windows: install.bat -Uninstall)   removes the start-up entries and the Desktop
  link. Nothing in your browser is ever changed or deleted by the installer.

Chrome may ask once to allow EYE3 Home to talk to apps on this computer. Choose Allow.

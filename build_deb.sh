#!/usr/bin/env bash
set -e
NAME=c-file-organizer
VER=1.0.0
PKG=build/${NAME}_${VER}_all

[ -f LICENSE ] || { echo "LICENSE file not found in $(pwd)"; exit 1; }

rm -rf build && mkdir -p \
  $PKG/DEBIAN $PKG/opt/$NAME $PKG/usr/bin \
  $PKG/usr/share/applications $PKG/usr/share/icons/hicolor/512x512/apps \
  $PKG/usr/share/doc/$NAME

cp core.py gui.py app.png $PKG/opt/$NAME/
cp app.png $PKG/usr/share/icons/hicolor/512x512/apps/$NAME.png
cp LICENSE $PKG/usr/share/doc/$NAME/copyright

cat > $PKG/usr/bin/$NAME <<'EOF'
#!/bin/sh
exec python3 /opt/c-file-organizer/gui.py "$@"
EOF

cat > $PKG/usr/share/applications/$NAME.desktop <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Chanakya's File Organizer
Comment=Rename and sort files into year/month/type folders
Exec=$NAME
Icon=$NAME
Terminal=false
Categories=Utility;FileTools;
Keywords=files;organize;sort;
StartupWMClass=c-file-organizer
EOF

cat > $PKG/DEBIAN/control <<EOF
Package: $NAME
Version: $VER
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-pyqt6
Maintainer: Chanakya Kumar Das <chanakyakumardas@hotmail.com>
Homepage: https://github.com/chanakyakumardas/c-file-organizer
Description: Chanakya's File Organizer
 A minimal desktop app that tidies up cluttered folders.
 Licensed under the MIT License.
EOF

cat > $PKG/DEBIAN/postinst <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -f /usr/share/icons/hicolor || true
exit 0
EOF
cp $PKG/DEBIAN/postinst $PKG/DEBIAN/postrm

find $PKG -type d -exec chmod 755 {} +
find $PKG -type f -exec chmod 644 {} +
chmod 755 $PKG/usr/bin/$NAME $PKG/DEBIAN/postinst $PKG/DEBIAN/postrm
chmod 755 $PKG/opt/$NAME/gui.py

dpkg-deb --build --root-owner-group $PKG
echo "Built: build/${NAME}_${VER}_all.deb"

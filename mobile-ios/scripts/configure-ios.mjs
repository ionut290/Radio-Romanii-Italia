import { readFile, writeFile } from "node:fs/promises";

const path = "ios/App/App/Info.plist";
let plist = await readFile(path, "utf8");
if (!plist.includes("<key>UIBackgroundModes</key>")) {
  plist = plist.replace("</dict>", "  <key>UIBackgroundModes</key>\n  <array>\n    <string>audio</string>\n  </array>\n</dict>");
}
await writeFile(path, plist);

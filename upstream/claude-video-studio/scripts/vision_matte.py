#!/usr/bin/env python3
"""Apple Vision mattes as a small importable helper (macOS only; everything returns None elsewhere).
  tool(kind)                 path of the compiled Swift helper, built once with swiftc into ~/.cache/claude-video-studio
  run_dir(kind, src, dst)    masks for every PNG/JPG in src -> dst/<name>.png (8-bit, image size); True on success
  mask_of(rgb, kind)         one image (numpy RGB uint8) -> float mask 0..1, or None
kind: "vision"    person segmentation, quality "accurate" (macOS 12+): people, with clean hair and limbs
      "vision-fg" foreground-instance masks, "lift subject" (macOS 14+): people AND what they hold or ride
No model download: the models ship with macOS. Needs the Xcode command line tools (swiftc)."""
import os, sys, subprocess, shutil, platform, tempfile

SWIFT = {
    "vision": '''import Vision
import CoreImage
import Foundation
let a = CommandLine.arguments
let inDir = URL(fileURLWithPath: a[1]), outDir = URL(fileURLWithPath: a[2])
let files = try! FileManager.default.contentsOfDirectory(atPath: inDir.path).filter { $0.hasSuffix(".png") || $0.hasSuffix(".jpg") }.sorted()
let ctx = CIContext()
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
for f in files {
  autoreleasepool {
    let ci = CIImage(contentsOf: inDir.appendingPathComponent(f))!
    let h = VNImageRequestHandler(ciImage: ci)
    try! h.perform([req])
    var m = CIImage(cvPixelBuffer: req.results!.first!.pixelBuffer)
    m = m.transformed(by: CGAffineTransform(scaleX: ci.extent.width / m.extent.width, y: ci.extent.height / m.extent.height))
    let name = (f as NSString).deletingPathExtension + ".png"
    try! ctx.writePNGRepresentation(of: m, to: outDir.appendingPathComponent(name), format: .L8, colorSpace: CGColorSpaceCreateDeviceGray())
  }
}
print("masks:", files.count)
''',
    "vision-fg": '''import Vision
import CoreImage
import Foundation
let a = CommandLine.arguments
let inDir = URL(fileURLWithPath: a[1]), outDir = URL(fileURLWithPath: a[2])
let files = try! FileManager.default.contentsOfDirectory(atPath: inDir.path).filter { $0.hasSuffix(".png") || $0.hasSuffix(".jpg") }.sorted()
let ctx = CIContext()
let gray = CGColorSpaceCreateDeviceGray()
var n = 0
for f in files {
  autoreleasepool {
    let ci = CIImage(contentsOf: inDir.appendingPathComponent(f))!
    let h = VNImageRequestHandler(ciImage: ci)
    let req = VNGenerateForegroundInstanceMaskRequest()
    let url = outDir.appendingPathComponent((f as NSString).deletingPathExtension + ".png")
    do {
      try h.perform([req])
      if let obs = req.results?.first {
        let pb = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: h)
        try ctx.writePNGRepresentation(of: CIImage(cvPixelBuffer: pb), to: url, format: .L8, colorSpace: gray)
        n += 1
      } else {
        try ctx.writePNGRepresentation(of: CIImage(color: .black).cropped(to: ci.extent), to: url, format: .L8, colorSpace: gray)
      }
    } catch { FileHandle.standardError.write("fgmask: \\(f): \\(error)\\n".data(using: .utf8)!) }
  }
}
print("masks:", n, "of", files.count)
''',
}



def tool(kind):
    """Path of the compiled Swift helper, or None when unavailable (not macOS, no swiftc, compile error)."""
    if platform.system() != "Darwin" or not shutil.which("swiftc"): return None
    cache = os.path.expanduser("~/.cache/claude-video-studio"); os.makedirs(cache, exist_ok=True)
    exe = os.path.join(cache, "matte-" + kind)
    srcf = exe + ".swift"
    if not os.path.exists(exe) or not os.path.exists(srcf) or open(srcf).read() != SWIFT[kind]:
        open(srcf, "w").write(SWIFT[kind])
        r = subprocess.run(["swiftc", "-O", srcf, "-o", exe], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"vision_matte: could not compile the {kind} helper:\n{r.stderr[-600:]}", file=sys.stderr); return None
    return exe


def run_dir(kind, src, dst):
    exe = tool(kind)
    if not exe: return False
    os.makedirs(dst, exist_ok=True)
    r = subprocess.run([exe, src, dst], capture_output=True, text=True)
    if r.returncode != 0: print(f"vision_matte: {kind} failed: {(r.stderr or r.stdout)[-300:]}", file=sys.stderr)
    return r.returncode == 0


def mask_of(rgb, kind="vision"):
    """Mask for one RGB uint8 image as float32 0..1 (same size), or None when Vision is unavailable."""
    if not tool(kind): return None
    import numpy as np, cv2
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "i")); cv2.imwrite(os.path.join(d, "i", "a.png"), rgb[..., ::-1])
        if not run_dir(kind, os.path.join(d, "i"), os.path.join(d, "o")): return None
        m = cv2.imread(os.path.join(d, "o", "a.png"), 0)
    if m is None: return None
    if m.shape != rgb.shape[:2]: m = cv2.resize(m, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
    return m.astype(np.float32) / 255

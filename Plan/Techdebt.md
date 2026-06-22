# KineTwin — Tech Debt

> รายการสิ่งที่ "ยังไม่สมบูรณ์/หยาบ" + ลำดับความสำคัญ · อัปเดต 2026-06-22
> (ซื่อตรง เพื่อจัดการต่อได้ถูกจุด)

---

## 🔴 P0 — ต้องแก้ก่อนเดโม hackathon (เสี่ยงคะแนน)

### T-001 · Real-video path ยังไม่เคย validate
- **ปัญหา:** MediaPipe บนวิดีโอมือจริงยังไม่เคยลอง (test แค่ synthetic landmarks)
- **ความเสี่ยง:** อัปโหลยบนคลิปจริงแล้ว track เพี้ยน/ไม่เจอมือ → เดโมพัง
- **แก้:** ถ่ายคลิปมือจริง → รัน validate offline → ถ้า track ไม่ดี ปรับสเปคถ่าย; คลิปตัวอย่าง pre-bake ไว้เลย

### T-002 · Speed calibration (relative-scale)
- **ปัญหา:** mean_speed ของ reference (Blender, เมตร) vs patient (MediaPipe world, relative-metric) ต่างสเกล → "% ช้ากว่าปกติ" อาจไม่แม่น
- **ความเสี่ยง:** คะแนน Speed บนวิดีโอจริงอาจออกมาแปลก
- **แก้:** normalize หรือสอบเทียบ scale ก่อนเทียบ speed (Accuracy/Quality scale-invariant อยู่แล้ว)

### T-003 · Reference model เป็น skeleton ชั่วคราว
- **ปัญหา:** asset #4 (Sketchfab "First Person hands") rig พังใน Blender (mesh พับตอน pose) → ใช้ procedural skeleton ไปก่อน
- **แก้:** รอ model มือใหม่จากนายท่าน → แปะเข้า rig → export trajectory ใหม่ (contract เดียวกัน `(T,21,3)`)

---

## 🟡 P1 — หลังเดโม

### T-004 · MediaPipe รัน 2 รอบใน `/analyze-one`
- **ปัญหา:** `track_video()` (world landmarks) + `extract_overlay_landmarks()` (image landmarks) แยก iterate วิดีโอ 2 ครั้ง = ช้า 2 เท่า
- **แก้:** refactor ให้ capture world + image ใน 1 pass (extend `FrameDetection`)

### T-005 · Overlay sync อาจคลาดเคลื่อน
- **ปัญหา:** overlay ใช้ `round(currentTime * fps)` map เฟรม; ถ้า fps ของวิดีโอไม่คงที่/ต่าง backend → อาจคลาด
- **แก้:** ใช้ pts หรือ resample overlay ตาม duration

### T-006 · CORS เปิดหมด (`allow_origins=["*"]`)
- **ปัญหา:** สะดวกตอน dev/demo แต่ไม่ปลอดภัยถ้า production จริง
- **แก้:** restrict ตาม origin ของ frontend เมื่อใช้จริง

### T-007 · Test ทั้งหมดเป็น synthetic
- **ปัญหา:** ไม่มี fixture วิดีโอจริง → regression บน real-video ไม่ถูกจับ
- **แก้:** เพิ่ม fixture วิดีโอจริง (small) + expected landmarks/scores

---

## 🟢 P2 — nice-to-have / expand

### T-008 · ไม่มี persistence (stateless)
- **ปัญปัญหา:** ไม่มี DB/session → ผู้ใช้กลับมาไม่เห็นประวัติ
- **แก้:** เพิ่ม (optional) เก็บผลใน localStorage หรือ DB เบาๆ

### T-009 · ไม่มี live camera mode
- **ปัญหา:** ต้องอัปโหลดไฟล์เท่านั้น
- **แก้:** MediaPipe Web (WASM) ใน browser → real-time + ลด load server

### T-010 · Cloud Run ใช้ project ร่วม SCAFFOLD
- **ปัญปัญหา:** `gen-lang-client-0658701327` ร่วม project (แม้ repo/service แยก `kinetwin-*`)
- **ความเสี่ยง:** ปน billing/quota (ตอนนี้ SCAFFOLD ยังไม่มีคนใช้ จึงไม่มีปัญหา)
- **แก้:** ถ้าใช้จริง long-term → สร้าง GCP project คนละตัว หรือย้ายไป host ฟรี (Render/HF/Cloudflare)

### T-011 · Frontend ยังไม่ responsive บนมือถือ
- **ปัญปัญหา:** split-screen 500px ออกแบบบน desktop
- **แก้:** ปรับ breakpoint / ปุ่ม full-screen สำหรับมือถือ (กรรมการอาจลองบนมือถือ)

### T-012 · cloudbuild ใช้ tag `:latest` เท่านั้น
- **ปัญปัญหา:** เอา `:${SHORT_SHA}` ออกตอน debug → ไม่มี version pin
- **แก้:** คืน `:$(git rev-parse --short HEAD)` ตอน production

---

## 📊 สรุป debt
- **หนักจริง 3 ข้อ (P0):** real-video validation, speed calibration, model swap — เป็นตัวแปรเดโมทั้งหมด
- **ที่เหลือ** = polish/robustness/expand — ทำหลังส่งได้

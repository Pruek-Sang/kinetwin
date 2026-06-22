# KineTwin — Roadmap

> แผนงานโปรเจกต์ · อัปเดต 2026-06-22

## 🎯 เป้าหมาย
**KineTwin** = ระบบคัดกรองภาวะ **Learned Non-Use** ในผู้สูงอายุ จาก **วิดีโอมือทำภารกิจ Reach-Grasp-Lift**
(ยกแก้ว) ผ่านกล้องมือถือ โดยวัด **Speed / Accuracy / Quality** และเทียบกับ **Kinematic Digital Twin**
เพื่อทำนายมือข้างที่ "ลืมใช้" — เน้นความเข้าถึงง่าย + AI โปร่งใส (MediaPipe + math)

---

## ✅ สถานะปัจจุบัน (MVP v0.1)

| # | ชั้น | สถานะ | commit |
|---|---|---|---|
| ① | AI metrics (Speed/Acc/Quality + scorer) | ✅ เสร็จ · 16 tests | `db1199f` |
| ② | AI tracking (MediaPipe → landmarks + pipeline) | ✅ เสร็จ · 7 tests | `bba2009` |
| ③ | Backend FastAPI (`/analyze*`) | ✅ เสร็จ · 4 tests | `0bf11f8` |
| ④ | Reference (kinematic skeleton, 21-landmark export) | ✅ interim (รอ model มือใหม่) | `7b3e156` |
| ⑤ | Frontend (split-screen + overlay + score panel) | ✅ เสร็จ | `4ea5804` |
| ⑥ | Deploy (Cloud Run 2 services + Docker) | ✅ ลอยบน cloud | `7509d9a` |

**Live:** frontend `kinetwin-frontend-...a.run.app` · backend `kinetwin-backend-...a.run.app`
**Repo:** github.com/Pruek-Sang/kinetwin · **27 tests ผ่าน** · **แยกจาก SCAFFOLD** 100%

---

## 🔴 Priority ถัดไป (เรียงความสำคัญ)

### P0 — ก่อนส่ง hackathon (ตัวแปรคะแนนเดโม)
- [ ] **ถ่ายวิดีโอมือจริง 2 คลิป** (มือปกติ + มือช้า/อ่อนแรง) ตามสเปคถ่าย
- [ ] **Validate MediaPipe track บนคลิปจริง** (offline 1 รอบ) → ปรับจน track ดี
- [ ] **Pre-bake** overlay + คะแนน → ฝังเป็นตัวอย่างในแอป (ปุ่ม "มือปกติ/มืออ่อนแรง")
- [ ] **ปรับ UI เป็น MVP สวย** (ปุ่มตัวอย่าง, loading, ความสะอาด)
- [ ] **อัดคลิปเดโม YouTube** (≤10 นาที, 1080p, Unlisted) + ชื่อกลุ่ม/สมาชิกใน description
- [ ] **เตรียมคำตอบ Q&A** (ความแม่นยำ, clinical validation, ทำไม MediaPipe)

### P1 — หลังเดโม / ปรับปรุงเล็ก
- [ ] แก้ speed calibration (real-video relative-scale)
- [ ] ลดการรัน MediaPipe 2 รอบใน `/analyze-one` (track + overlay รวมเป็น 1 pass)
- [ ] สลับ model มืออ้างอิงเป็นของสมจริง (เมื่อได้ model ใหม่)

### P2 — อนาคต (expand)
- [ ] **Live camera** (MediaPipe Web ใน browser — real-time + ประหยัด server)
- [ ] ขยายไป body parts อื่น (MediaPipe Pose — แขน/ขา/ตัว) **ถ้ามีเวลา/โจทย์ขยาย**
- [ ] การเก็บประวัติ/history (persistence)
- [ ] clinical validation + สอบเทียบกับมาตรฐาน
- [ ] ทดสอบด้วยข้อมูลจริง (real patient dataset)

---

## 🗺️ Roadmap เฟส
| เฟส | สิ่งที่ได้ | สถานะ |
|---|---|---|
| **v0.1 MVP** | upload + split-screen + overlay + 3 คะแนน + LNU flag (Cloud Run) | ✅ done |
| **v0.2 Demo-ready** | ตัวอย่าง pre-baked + UI สวย + คลิปเดโม | 🔨 กำลังทำ (P0) |
| **v0.3 Real-time** | live webcam (MediaPipe Web), ทุกอย่างใน browser | ⏳ P2 |
| **v1.0 Clinical** | validated + multi-task + persistence | ⏳ อนาคต |

---

## 🧭 หลักการตัดสินใจ
- **AI น้อยที่สุด + โปร่งใส** (MediaPipe + math) — เหมาะกลางการแพทย์
- **เน้นมือ/Reach-Grasp-Lift** (ตรง Learned Non-Use) — ไม่บานไป body parts จนตื้น
- **แยกชัดเจน** (layered) + **แยกจากงานอื่น** (isolated repo/services)

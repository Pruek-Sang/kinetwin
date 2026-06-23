import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

interface Props {
  playing: boolean;
}

/**
 * Loads the reference_hand.glb (exported from Blender) and renders
 * it as a real 3D scene with animation, lights, and orbit controls.
 * This gives pixel-perfect visual parity with the Blender viewport.
 */
export function ReferenceSkeletonPlayer({ playing }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const lastTimeRef = useRef(performance.now());
  const actionRef = useRef<THREE.AnimationAction | null>(null);
  const rafRef = useRef(0);
  const [loaded, setLoaded] = useState(false);
  const [frameInfo, setFrameInfo] = useState("Loading…");

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070b12);

    // Camera
    const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100);
    camera.position.set(0.15, 0.35, 0.45);
    camera.lookAt(0, 0.25, 0.0);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    rendererRef.current = renderer;
    mount.appendChild(renderer.domElement);

    // Controls (orbit around the hand)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0.25, 0.0);
    controls.minDistance = 0.1;
    controls.maxDistance = 2;
    controls.update();

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xfff5e6, 1.5);
    keyLight.position.set(0.5, 1, 0.8);
    keyLight.castShadow = false;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xd4e5ff, 0.5);
    fillLight.position.set(-0.5, 0.5, -0.3);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0x22d3ee, 0.3);
    rimLight.position.set(0, 0.3, -1);
    scene.add(rimLight);

    // Grid floor (subtle) - positioned at ground level
    const gridHelper = new THREE.GridHelper(1, 20, 0x1d2937, 0x0e1622);
    gridHelper.position.y = -0.02;
    scene.add(gridHelper);

    // Load the GLB
    const loader = new GLTFLoader();
    loader.load(
      "/reference_hand.glb",
      (gltf) => {
        // Apply Premium Medical Holographic Materials
        gltf.scene.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            const name = mesh.name.toLowerCase();

            if (name.includes("cup")) {
              // Frosted Red Glass
              mesh.material = new THREE.MeshPhysicalMaterial({
                color: 0xf87171, // kt-red
                transmission: 0.7,
                opacity: 1,
                transparent: true,
                roughness: 0.35,
                ior: 1.5,
                side: THREE.DoubleSide,
              });
            } else if (name.includes("sphere") || name.includes("joint")) {
              // Neon Joints (Cyan)
              mesh.material = new THREE.MeshStandardMaterial({
                color: 0x22d3ee, // kt-cyan
                emissive: 0x22d3ee,
                emissiveIntensity: 1.2,
                roughness: 0.2,
                metalness: 0.8,
              });
            } else {
              // Holographic / X-Ray Bones (Glassmorphism)
              mesh.material = new THREE.MeshPhysicalMaterial({
                color: 0xffffff,
                emissive: 0x22d3ee,
                emissiveIntensity: 0.15,
                transmission: 0.9,
                opacity: 1,
                transparent: true,
                roughness: 0.1,
                ior: 1.2,
                clearcoat: 1.0,
                clearcoatRoughness: 0.1,
              });
            }
          }
        });

        scene.add(gltf.scene);

        // Setup animation
        if (gltf.animations.length > 0) {
          const mixer = new THREE.AnimationMixer(gltf.scene);
          mixerRef.current = mixer;
          const action = mixer.clipAction(gltf.animations[0]);
          action.setLoop(THREE.LoopRepeat, Infinity);
          actionRef.current = action;
        }

        setLoaded(true);
        setFrameInfo("Ready · Press Play");
      },
      undefined,
      (err) => {
        console.error("GLB load error:", err);
        setFrameInfo("Error loading 3D model");
      }
    );

    // Resize handler
    const onResize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(mount);
    onResize();

    // Animation loop
    const animate = () => {
      rafRef.current = requestAnimationFrame(animate);
      const now = performance.now();
      const delta = (now - lastTimeRef.current) / 1000;
      lastTimeRef.current = now;

      if (mixerRef.current) {
        mixerRef.current.update(delta);

        // Update frame info
        const action = actionRef.current;
        if (action) {
          const clip = action.getClip();
          const time = action.time;
          const frame = Math.round(time * 30); // 30fps
          const totalFrames = Math.round(clip.duration * 30);

          let phase = "REST";
          if (frame >= 1 && frame < 30) phase = "REACH";
          else if (frame >= 30 && frame < 45) phase = "GRASP";
          else if (frame >= 45 && frame < 72) phase = "LIFT";
          else if (frame >= 72) phase = "HOLD";

          setFrameInfo(`Frame ${frame}/${totalFrames} · ${phase}`);
        }
      }

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(rafRef.current);
      resizeObserver.disconnect();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  // Play/Pause control
  useEffect(() => {
    const action = actionRef.current;
    if (!action) return;
    if (playing) {
      action.paused = false;
      action.play();
      lastTimeRef.current = performance.now();
    } else {
      action.paused = true;
    }
  }, [playing]);

  return (
    <div className="relative h-full w-full">
      <div ref={mountRef} className="h-full w-full" />
      {/* Phase & frame overlay */}
      <div className="pointer-events-none absolute bottom-2 left-2 rounded bg-black/60 px-2 py-0.5 text-[10px] font-mono text-kt-cyan backdrop-blur-sm">
        {frameInfo}
      </div>
      {/* Orbit hint */}
      <div className="pointer-events-none absolute top-2 left-2 rounded bg-black/40 px-2 py-0.5 text-[9px] text-kt-muted backdrop-blur-sm">
        🖱 Drag to orbit · Scroll to zoom
      </div>
    </div>
  );
}

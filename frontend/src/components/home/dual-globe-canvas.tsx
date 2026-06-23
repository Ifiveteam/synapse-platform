import * as THREE from "three";
import { useEffect, useMemo, useRef } from "react";

import type { EmbeddingGraphData } from "@/api/indexer";
import { toCatalogForceGraph, type CatalogForceNode } from "@/lib/analyses/embedding-graph-data";

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const GLOBE_R = 110;
const MAX_GLOBES = 5;
const ATM_COLORS = [0x4466ee, 0x2288ff, 0xa855f7, 0x22d3ee, 0xf97316];
const ROT_SPEEDS = [0.003, -0.002, 0.0025, -0.0018, 0.0022];

interface GlobeBuffers {
  positions: Float32Array;
  colors: Float32Array;
}

function buildBuffers(data: EmbeddingGraphData): GlobeBuffers {
  const g = toCatalogForceGraph(data, null);
  const nodes = g.nodes as CatalogForceNode[];
  const n = nodes.length;
  const positions = new Float32Array(n * 3);
  const colors = new Float32Array(n * 3);
  const c = new THREE.Color();
  nodes.forEach((node, i) => {
    const yNorm = 1 - (i / Math.max(n - 1, 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - yNorm * yNorm));
    const theta = GOLDEN_ANGLE * i;
    positions[i * 3] = r * Math.cos(theta) * GLOBE_R;
    positions[i * 3 + 1] = yNorm * GLOBE_R;
    positions[i * 3 + 2] = r * Math.sin(theta) * GLOBE_R;
    c.set(node.color ?? "#818cf8");
    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  });
  return { positions, colors };
}

interface Props {
  data: EmbeddingGraphData[];
  labels?: string[];
  width: number;
  height: number;
  onGlobeClick?: (index: number) => void;
}

export function DualGlobeCanvas({ data, labels = [], width, height, onGlobeClick }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const bufs = useMemo(() => data.slice(0, MAX_GLOBES).map(buildBuffers), [data]);
  const count = Math.min(data.length, MAX_GLOBES);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || width === 0 || height === 0 || count === 0) return;

    const n = count;
    const sep = n <= 1 ? 0 : Math.min(480, 1600 / (n - 1));
    const span = sep * Math.max(n - 1, 0);
    const initR = Math.max(880, span * 1.35);
    const xPositions = Array.from({ length: n }, (_, i) => -span / 2 + i * sep);

    // ── Scene ──
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#03050a");

    const bgGeo = new THREE.BufferGeometry();
    const bgPos = new Float32Array(3000 * 3);
    for (let i = 0; i < 3000; i++) {
      bgPos[i * 3] = (Math.random() - 0.5) * 4000;
      bgPos[i * 3 + 1] = (Math.random() - 0.5) * 4000;
      bgPos[i * 3 + 2] = (Math.random() - 0.5) * 4000;
    }
    bgGeo.setAttribute("position", new THREE.BufferAttribute(bgPos, 3));
    const bgMat = new THREE.PointsMaterial({ size: 0.7, color: 0xffffff, transparent: true, opacity: 0.3, sizeAttenuation: true });
    scene.add(new THREE.Points(bgGeo, bgMat));

    // ── Camera ──
    const camera = new THREE.PerspectiveCamera(52, width / height, 1, 8000);
    let spherR = initR, spherTheta = 0, spherPhi = Math.PI * 0.40;
    const updateCamera = () => {
      camera.position.set(
        spherR * Math.sin(spherPhi) * Math.cos(spherTheta),
        spherR * Math.cos(spherPhi),
        spherR * Math.sin(spherPhi) * Math.sin(spherTheta),
      );
      camera.lookAt(0, 0, 0);
    };
    updateCamera();

    // ── Renderer ──
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    // ── Globes ──
    const globeObjects = bufs.map((buf, i) => {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(buf.positions, 3));
      geo.setAttribute("color", new THREE.BufferAttribute(buf.colors, 3));
      const mat = new THREE.PointsMaterial({
        size: 3.8, vertexColors: true, sizeAttenuation: true,
        transparent: true, opacity: 0.9,
      });
      const pts = new THREE.Points(geo, mat);
      pts.position.x = xPositions[i];
      scene.add(pts);
      return { pts, geo, mat };
    });

    // ── Colliders & Atmosphere ──
    const colliderGeo = new THREE.SphereGeometry(GLOBE_R * 1.1, 16, 16);
    const atmGeo = new THREE.SphereGeometry(GLOBE_R * 1.15, 32, 32);
    const colliders: THREE.Mesh[] = [];

    xPositions.forEach((x, i) => {
      const col = new THREE.Mesh(
        colliderGeo,
        new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
      );
      col.position.x = x;
      scene.add(col);
      colliders.push(col);

      const atm = new THREE.Mesh(
        atmGeo,
        new THREE.MeshBasicMaterial({ color: ATM_COLORS[i % ATM_COLORS.length], transparent: true, opacity: 0.035 }),
      );
      atm.position.x = x;
      scene.add(atm);
    });

    // ── Interaction ──
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let dragging = false, lx = 0, ly = 0, didDrag = false;

    const onDown = (e: MouseEvent) => { dragging = true; didDrag = false; lx = e.clientX; ly = e.clientY; };
    const onMove = (e: MouseEvent) => {
      if (dragging) {
        const dx = e.clientX - lx, dy = e.clientY - ly;
        if (Math.abs(dx) + Math.abs(dy) > 3) didDrag = true;
        spherTheta -= dx * 0.005;
        spherPhi = Math.max(0.08, Math.min(Math.PI - 0.08, spherPhi + dy * 0.005));
        lx = e.clientX; ly = e.clientY;
        updateCamera();
      }
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects(colliders);
      renderer.domElement.style.cursor = hits.length > 0 ? "pointer" : dragging ? "grabbing" : "grab";
    };
    const onUp = () => { dragging = false; };

    const onClick = (e: MouseEvent) => {
      if (didDrag) return;
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects(colliders);
      if (hits.length > 0) {
        const idx = colliders.indexOf(hits[0].object as THREE.Mesh);
        if (idx !== -1) onGlobeClick?.(idx);
      }
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      spherR = Math.max(200, Math.min(4000, spherR * (e.deltaY > 0 ? 1.08 : 0.93)));
      updateCamera();
    };

    let lastPinch = 0;
    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2)
        lastPinch = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    };
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length !== 2) return;
      e.preventDefault();
      const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      if (lastPinch > 0) { spherR = Math.max(200, Math.min(4000, spherR * (lastPinch / d))); updateCamera(); }
      lastPinch = d;
    };

    const cvs = renderer.domElement;
    cvs.addEventListener("mousedown", onDown);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    cvs.addEventListener("click", onClick);
    cvs.addEventListener("wheel", onWheel, { passive: false });
    cvs.addEventListener("touchstart", onTouchStart, { passive: false });
    cvs.addEventListener("touchmove", onTouchMove, { passive: false });

    // ── Animation ──
    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      globeObjects.forEach((g, i) => { g.pts.rotation.y += ROT_SPEEDS[i % ROT_SPEEDS.length]; });
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      cvs.removeEventListener("mousedown", onDown);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      cvs.removeEventListener("click", onClick);
      cvs.removeEventListener("wheel", onWheel);
      cvs.removeEventListener("touchstart", onTouchStart);
      cvs.removeEventListener("touchmove", onTouchMove);
      renderer.dispose();
      globeObjects.forEach((g) => { g.geo.dispose(); g.mat.dispose(); });
      bgGeo.dispose(); bgMat.dispose();
      colliderGeo.dispose(); atmGeo.dispose();
      if (mount.contains(cvs)) mount.removeChild(cvs);
    };
  }, [bufs, width, height, onGlobeClick, count]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl" style={{ backgroundColor: "#03050a" }}>
      <div ref={mountRef} className="h-full w-full" />
      <p className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 text-[10px] text-white/25">
        클릭하여 자세히 보기 · 드래그로 회전 · 스크롤로 줌
      </p>
      {labels.slice(0, count).map((label, i) => (
        <div
          key={i}
          className="pointer-events-none absolute bottom-4"
          style={{
            left: `${((i + 0.5) / count) * 100}%`,
            transform: "translateX(-50%) translateY(-28px)",
          }}
        >
          <span className="rounded-full bg-black/50 px-3 py-1 text-[11px] font-semibold text-white/80 backdrop-blur-sm">
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}

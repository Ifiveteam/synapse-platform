import * as THREE from "three";
import { useEffect, useMemo, useRef } from "react";

import type { EmbeddingGraphData } from "@/api/indexer";
import { toCatalogForceGraph, type CatalogForceNode } from "@/lib/analyses/embedding-graph-data";

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const GLOBE_R = 110;
const SEP = 380; // 더 넓은 공간

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
    colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
  });
  return { positions, colors };
}

interface Props {
  data1: EmbeddingGraphData;
  data2: EmbeddingGraphData;
  label1?: string;
  label2?: string;
  width: number;
  height: number;
  onGlobeClick?: (globe: 1 | 2) => void;
}

export function DualGlobeCanvas({
  data1, data2,
  label1 = "분석 1", label2 = "분석 2",
  width, height,
  onGlobeClick,
}: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const buf1 = useMemo(() => buildBuffers(data1), [data1]);
  const buf2 = useMemo(() => buildBuffers(data2), [data2]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || width === 0 || height === 0) return;

    // ── Scene ──
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#03050a");

    // 우주 배경 별
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
    let spherR = 780, spherTheta = 0, spherPhi = Math.PI * 0.40;
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

    // ── Globe 파티클 ──
    const makeGlobe = (buf: GlobeBuffers, x: number) => {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(buf.positions, 3));
      geo.setAttribute("color", new THREE.BufferAttribute(buf.colors, 3));
      const mat = new THREE.PointsMaterial({
        size: 3.8, vertexColors: true, sizeAttenuation: true,
        transparent: true, opacity: 0.9,
      });
      const pts = new THREE.Points(geo, mat);
      pts.position.x = x;
      scene.add(pts);
      return { pts, geo, mat };
    };
    const g1 = makeGlobe(buf1, -SEP / 2);
    const g2 = makeGlobe(buf2, SEP / 2);

    // ── 클릭 감지용 투명 구 콜라이더 ──
    const colliderGeo = new THREE.SphereGeometry(GLOBE_R * 1.1, 16, 16);
    const colliderMat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
    const col1 = new THREE.Mesh(colliderGeo, colliderMat);
    col1.position.x = -SEP / 2;
    const col2 = new THREE.Mesh(colliderGeo, colliderMat.clone());
    col2.position.x = SEP / 2;
    scene.add(col1, col2);

    // ── 대기권 글로우 ──
    const atmGeo = new THREE.SphereGeometry(GLOBE_R * 1.15, 32, 32);
    for (const [x, col] of [[-SEP / 2, 0x4466ee], [SEP / 2, 0x2288ff]] as [number, number][]) {
      const atm = new THREE.Mesh(atmGeo, new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.035 }));
      atm.position.x = x;
      scene.add(atm);
    }

    // ── 인터랙션 ──
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
      // 호버 커서
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects([col1, col2]);
      renderer.domElement.style.cursor = hits.length > 0 ? "pointer" : dragging ? "grabbing" : "grab";
    };
    const onUp = () => { dragging = false; };

    const onClick = (e: MouseEvent) => {
      if (didDrag) return; // 드래그 후 클릭 무시
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects([col1, col2]);
      if (hits.length > 0) {
        onGlobeClick?.(hits[0].object === col1 ? 1 : 2);
      }
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      spherR = Math.max(200, Math.min(3000, spherR * (e.deltaY > 0 ? 1.08 : 0.93)));
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
      if (lastPinch > 0) { spherR = Math.max(200, Math.min(3000, spherR * (lastPinch / d))); updateCamera(); }
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

    // ── 애니메이션 ──
    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      g1.pts.rotation.y += 0.003;
      g2.pts.rotation.y -= 0.002;
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
      g1.geo.dispose(); g1.mat.dispose();
      g2.geo.dispose(); g2.mat.dispose();
      bgGeo.dispose(); bgMat.dispose();
      colliderGeo.dispose();
      if (mount.contains(cvs)) mount.removeChild(cvs);
    };
  }, [buf1, buf2, width, height, onGlobeClick]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl" style={{ backgroundColor: "#03050a" }}>
      <div ref={mountRef} className="h-full w-full" />
      {/* 클릭 힌트 */}
      <p className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 text-[10px] text-white/25">
        클릭하여 자세히 보기 · 드래그로 회전 · 스크롤로 줌
      </p>
      {/* 레이블 */}
      <div className="pointer-events-none absolute bottom-4 left-[27%] -translate-x-1/2 translate-y-[-28px]">
        <span className="rounded-full bg-black/50 px-3 py-1 text-[11px] font-semibold text-white/80 backdrop-blur-sm">
          {label1}
        </span>
      </div>
      <div className="pointer-events-none absolute bottom-4 left-[73%] -translate-x-1/2 translate-y-[-28px]">
        <span className="rounded-full bg-black/50 px-3 py-1 text-[11px] font-semibold text-white/80 backdrop-blur-sm">
          {label2}
        </span>
      </div>
    </div>
  );
}

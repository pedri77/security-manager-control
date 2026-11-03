// Entrada del bundle: solo lo que usa el visor (tree-shaking). Ver docs/adr/ADR-004-three-js-vendorizado.md
export {
  WebGLRenderer, Scene, PerspectiveCamera, Color, Group, Mesh, Sprite,
  BoxGeometry, CylinderGeometry, OctahedronGeometry, SphereGeometry, PlaneGeometry, EdgesGeometry,
  MeshLambertMaterial, MeshBasicMaterial, LineBasicMaterial, SpriteMaterial,
  LineSegments, AmbientLight, DirectionalLight, Raycaster, Vector2, Vector3, CanvasTexture, SRGBColorSpace,
} from "THREE_SRC";

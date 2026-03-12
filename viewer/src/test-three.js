import * as THREE from "three";
console.log("THREE loaded:", typeof THREE, "Color:", typeof THREE.Color);

import * as OBC from "@thatopen/components";
console.log("OBC loaded:", typeof OBC, "Components:", typeof OBC.Components, "SimpleScene:", typeof OBC.SimpleScene);

const scene = new OBC.SimpleScene(new OBC.Components());
console.log("SimpleScene created OK");

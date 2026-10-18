(function (global) {
  "use strict";

  const SCARED_DISTANCE = 1;
  const MAP_WIDTH = 1000;
  const MAP_HEIGHT = 700;
  const COLORS = {
    background: "#f5f3ec",
    road: "#b7c4bf",
    node: "#ffffff",
    nodeBorder: "#60756e",
    label: "#24332f",
    goal: "#f2bd45",
    start: "#32a879",
    legal: "#27a8cc",
    student: "#2878e5",
    proctor: "#e25757",
    white: "#ffffff"
  };

  // Preload player state sprites and proctor sprite
  const PLAYER_SPRITES = {
    avg: "/assets/avg_player.jpg",
    scared: "/assets/scared_player.jpg",
    lose: "/assets/lose_player.jpg",
    win: "/assets/win_player.jpg"
  };

  const loadedImages = {
    player: {
      avg: null,
      scared: null,
      lose: null,
      win: null
    },
    proctor: null
  };

  let currentStudentState = "avg"; // 'avg', 'scared', 'lose', 'win'
  let activeCanvas = null;
  let activeMap = null;
  let activeOptions = null;

  function preloadImage(url) {
    if (typeof global.Image === "undefined") return Promise.resolve(null);
    return new Promise(function (resolve) {
      const img = new global.Image();
      img.onload = function () {
        resolve(img);
      };
      img.onerror = function () {
        resolve(null);
      };
      img.src = url;
    });
  }

  // Kick off preloading
  Object.keys(PLAYER_SPRITES).forEach(function (stateKey) {
    preloadImage(PLAYER_SPRITES[stateKey]).then(function (img) {
      loadedImages.player[stateKey] = img;
    });
  });
  preloadImage("/assets/proctor.jpeg").then(function (img) {
    loadedImages.proctor = img;
  });

  function hopDistance(map, a, b) {
    if (!map || !Array.isArray(map.edges) || !a || !b) return Infinity;
    if (a === b) return 0;

    const adj = new Map();
    map.edges.forEach(function (e) {
      if (!adj.has(e.from)) adj.set(e.from, []);
      if (!adj.has(e.to)) adj.set(e.to, []);
      adj.get(e.from).push(e.to);
      adj.get(e.to).push(e.from);
    });

    const queue = [[a, 0]];
    const visited = new Set([a]);

    while (queue.length > 0) {
      const [curr, dist] = queue.shift();
      const neighbors = adj.get(curr) || [];
      for (let i = 0; i < neighbors.length; i++) {
        const nb = neighbors[i];
        if (nb === b) return dist + 1;
        if (!visited.has(nb)) {
          visited.add(nb);
          queue.push([nb, dist + 1]);
        }
      }
    }
    return Infinity;
  }

  function getNodeMap(map) {
    if (!map || !Array.isArray(map.nodes) || !Array.isArray(map.edges)) {
      throw new TypeError("Map must contain node and edge arrays");
    }
    const nodes = new Map();
    map.nodes.forEach(function (node) {
      if (
        !node ||
        typeof node.id !== "string" ||
        !Number.isFinite(node.x) ||
        !Number.isFinite(node.y) ||
        nodes.has(node.id)
      ) {
        throw new TypeError("Map nodes must have unique ids and finite x/y coordinates");
      }
      nodes.set(node.id, node);
    });
    return nodes;
  }

  function prepareCanvas(canvas) {
    if (!canvas || typeof canvas.getContext !== "function") {
      throw new TypeError("A canvas element is required");
    }

    const bounds = canvas.getBoundingClientRect();
    const width = bounds.width || canvas.clientWidth || canvas.width || MAP_WIDTH;
    const height = bounds.height || canvas.clientHeight || canvas.height || MAP_HEIGHT;
    const pixelRatio = global.devicePixelRatio || 1;
    const pixelWidth = Math.round(width * pixelRatio);
    const pixelHeight = Math.round(height * pixelRatio);
    if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
    if (canvas.height !== pixelHeight) canvas.height = pixelHeight;

    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Could not acquire a 2D canvas context");
    }

    const scale = Math.min(pixelWidth / MAP_WIDTH, pixelHeight / MAP_HEIGHT);
    const offsetX = (pixelWidth - MAP_WIDTH * scale) / 2;
    const offsetY = (pixelHeight - MAP_HEIGHT * scale) / 2;
    context.setTransform(scale, 0, 0, scale, offsetX, offsetY);
    return context;
  }

  function loadProctorPhoto(photo, onPhotoError) {
    if (loadedImages.proctor) return Promise.resolve(loadedImages.proctor);
    if (!photo) return Promise.resolve(null);
    if (typeof photo !== "string") {
      if (photo.complete && photo.naturalWidth > 0) {
        return Promise.resolve(photo);
      }
      return Promise.resolve(null);
    }

    return preloadImage(photo);
  }

  function drawDistancePill(context, x, y, text) {
    context.save();
    context.font = "600 11px system-ui, -apple-system, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    const tw = context.measureText(text).width;
    const pw = tw + 10;
    const ph = 16;
    const px = x - pw / 2;
    const py = y - ph / 2;
    const r = 4;

    context.beginPath();
    context.moveTo(px + r, py);
    context.lineTo(px + pw - r, py);
    context.arcTo(px + pw, py, px + pw, py + r, r);
    context.lineTo(px + pw, py + ph - r);
    context.arcTo(px + pw, py + ph, px + pw - r, py + ph, r);
    context.lineTo(px + r, py + ph);
    context.arcTo(px, py + ph, px, py + ph - r, r);
    context.lineTo(px, py + r);
    context.arcTo(px, py, px + r, py, r);
    context.closePath();

    context.fillStyle = "rgba(255, 255, 255, 0.94)";
    context.fill();
    context.strokeStyle = "#8da198";
    context.lineWidth = 1;
    context.stroke();

    context.fillStyle = "#24332f";
    context.fillText(text, x, y);
    context.restore();
  }

  function drawEdges(context, map, nodes, showDistances) {
    context.save();
    context.strokeStyle = COLORS.road;
    context.lineWidth = 3;
    context.lineCap = "round";
    map.edges.forEach(function (edge) {
      if (!edge || typeof edge.from !== "string" || typeof edge.to !== "string") {
        throw new TypeError("Map edges must have from and to node ids");
      }
      const from = nodes.get(edge.from);
      const to = nodes.get(edge.to);
      if (!from || !to) {
        throw new Error("Map edge references an unknown node");
      }
      context.beginPath();
      context.moveTo(from.x, from.y);
      const curve = Number(edge.curve) || 0;
      if (curve !== 0) {
        const midX = (from.x + to.x) / 2;
        const midY = (from.y + to.y) / 2;
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const len = Math.hypot(dx, dy) || 1;
        const nx = -dy / len;
        const ny = dx / len;
        const cpX = midX + nx * curve;
        const cpY = midY + ny * curve;
        context.quadraticCurveTo(cpX, cpY, to.x, to.y);
      } else {
        context.lineTo(to.x, to.y);
      }
      context.stroke();
    });
    context.restore();

    // Draw edge walking distance pill labels at the midpoint
    if (showDistances !== false && Array.isArray(map.edges)) {
      map.edges.forEach(function (edge) {
        if (edge.cost === undefined || edge.cost === null) return;
        const from = nodes.get(edge.from);
        const to = nodes.get(edge.to);
        if (!from || !to) return;

        let midX = (from.x + to.x) / 2;
        let midY = (from.y + to.y) / 2;
        const curve = Number(edge.curve) || 0;
        if (curve !== 0) {
          const dx = to.x - from.x;
          const dy = to.y - from.y;
          const len = Math.hypot(dx, dy) || 1;
          const nx = -dy / len;
          const ny = dx / len;
          const cpX = midX + nx * curve;
          const cpY = midY + ny * curve;
          // Quadratic Bezier midpoint at t = 0.5 is (mid + cp) / 2
          midX = (midX + cpX) / 2;
          midY = (midY + cpY) / 2;
        }

        drawDistancePill(context, midX, midY, edge.cost + " m");
      });
    }
  }

  function drawNode(context, node, map, options, legalMoves, allowedStarts) {
    const goalId = map && map.goal ? map.goal : "informatics";
    const isGoal = node.id === goalId;
    const isLegal = legalMoves.has(node.id);
    const isStart = options.choosingStart === true && allowedStarts.has(node.id);
    const radius = isGoal ? 13 : 8;

    if (isStart || isLegal) {
      context.save();
      context.beginPath();
      context.arc(node.x, node.y, radius + 8, 0, Math.PI * 2);
      context.strokeStyle = isLegal ? COLORS.legal : COLORS.start;
      context.lineWidth = 3;
      context.setLineDash(isStart && !isLegal ? [5, 4] : []);
      context.stroke();
      context.restore();
    }

    if (isGoal) {
      context.save();
      context.beginPath();
      context.arc(node.x, node.y, radius + 7, 0, Math.PI * 2);
      context.fillStyle = "rgba(242, 189, 69, 0.24)";
      context.fill();
      context.restore();
    }

    context.save();
    context.beginPath();
    context.arc(node.x, node.y, radius, 0, Math.PI * 2);
    context.fillStyle = isGoal ? COLORS.goal : COLORS.node;
    context.fill();
    context.lineWidth = isGoal ? 3 : 2;
    context.strokeStyle = isGoal ? "#a97512" : COLORS.nodeBorder;
    context.stroke();
    context.restore();

    const label = node.label || node.name || node.id;
    if (label) {
      drawLabel(context, node, label);
    }
  }

  function drawLabel(context, node, label) {
    context.save();
    context.font = "600 13px system-ui, sans-serif";
    context.textBaseline = "middle";
    const rightSide = node.x < MAP_WIDTH * 0.68;
    const textX = node.x + (rightSide ? 14 : -14);
    context.textAlign = rightSide ? "left" : "right";
    context.lineWidth = 4;
    context.lineJoin = "round";
    context.strokeStyle = COLORS.background;
    context.strokeText(label, textX, node.y, 220);
    context.fillStyle = COLORS.label;
    context.fillText(label, textX, node.y, 220);
    context.restore();
  }

  function drawPiece(context, x, y, piece, photo) {
    const studentImg = loadedImages.player[currentStudentState];
    const imgToDraw = piece === "proctor" ? photo : studentImg;

    // If image is loaded, draw as circular crop with radius 20 and white border
    if (imgToDraw && imgToDraw.complete && imgToDraw.naturalWidth > 0) {
      const radius = 20;
      context.save();
      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.clip();
      context.drawImage(imgToDraw, x - radius, y - radius, radius * 2, radius * 2);
      context.restore();

      context.save();
      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.lineWidth = 3;
      context.strokeStyle = COLORS.white;
      context.stroke();
      context.restore();
      return;
    }

    // Fallback: colored circle with white border
    const radius = 20;
    context.save();
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fillStyle = piece === "proctor" ? COLORS.proctor : COLORS.student;
    context.fill();
    context.lineWidth = 3;
    context.strokeStyle = COLORS.white;
    context.stroke();
    context.restore();
  }

  function drawPieces(context, state, nodes, photo, movingPiece, map) {
    if (!state && !movingPiece) return;
    if (state) {
      ["student", "proctor"].forEach(function (piece) {
        if (movingPiece && movingPiece.piece === piece) return;
        const node = nodes.get(state[piece]);
        if (!node) {
          throw new Error("Game state references an unknown " + piece + " node");
        }
        drawPiece(context, node.x, node.y, piece, piece === "proctor" ? photo : null);
      });
    }

    if (movingPiece) {
      const from = nodes.get(movingPiece.from);
      const to = nodes.get(movingPiece.to);
      if (!from || !to) {
        throw new Error("Animated move references an unknown node");
      }
      const progress = Math.max(0, Math.min(1, movingPiece.progress));
      let x = from.x + (to.x - from.x) * progress;
      let y = from.y + (to.y - from.y) * progress;

      // Check if there is a curved edge between from and to
      if (map && Array.isArray(map.edges)) {
        const edge = map.edges.find(function (e) {
          return (e.from === movingPiece.from && e.to === movingPiece.to) ||
                 (e.from === movingPiece.to && e.to === movingPiece.from);
        });
        if (edge && edge.curve) {
          const curveVal = (edge.from === movingPiece.from && edge.to === movingPiece.to)
            ? Number(edge.curve)
            : -Number(edge.curve);
          const midX = (from.x + to.x) / 2;
          const midY = (from.y + to.y) / 2;
          const dx = to.x - from.x;
          const dy = to.y - from.y;
          const len = Math.hypot(dx, dy) || 1;
          const nx = -dy / len;
          const ny = dx / len;
          const cpX = midX + nx * curveVal;
          const cpY = midY + ny * curveVal;
          const t = progress;
          const mt = 1 - t;
          x = mt * mt * from.x + 2 * mt * t * cpX + t * t * to.x;
          y = mt * mt * from.y + 2 * mt * t * cpY + t * t * to.y;
        }
      }

      drawPiece(
        context,
        x,
        y,
        movingPiece.piece,
        movingPiece.piece === "proctor" ? photo : null
      );
    }
  }

  function drawLegend(context, options, map) {
    if (options.showLegend === false) return;
    const width = 168;
    const height = options.choosingStart ? 104 : 84;
    // Positioned at bottom-left corner so Graha (top-left) and Electrical Eng (bottom-right) are completely unobstructed
    const x = 16;
    const y = MAP_HEIGHT - height - 16;

    context.save();
    context.fillStyle = "rgba(255, 255, 255, 0.94)";
    context.strokeStyle = "#d3ddd7";
    context.lineWidth = 1;
    context.beginPath();
    context.rect(x, y, width, height);
    context.fill();
    context.stroke();
    context.restore();

    let goalText = "Informatics (Goal)";
    if (map && Array.isArray(map.nodes)) {
      const gId = map.goal || "informatics";
      const gNode = map.nodes.find(function (n) { return n.id === gId; });
      if (gNode && gNode.label) {
        goalText = gNode.label + " (Goal)";
      }
    }

    drawLegendItem(context, COLORS.student, "Student", x + 16, y + 18);
    drawLegendItem(context, COLORS.proctor, "Proctor (TA)", x + 16, y + 38);
    drawLegendItem(context, COLORS.goal, goalText, x + 16, y + 58);
    if (options.choosingStart) {
      drawLegendItem(context, COLORS.start, "Available Start", x + 16, y + 78);
    }
  }

  function drawLegendItem(context, color, text, x, y) {
    context.save();
    context.beginPath();
    context.arc(x, y, 6, 0, Math.PI * 2);
    context.fillStyle = color;
    context.fill();
    context.restore();

    context.save();
    context.fillStyle = COLORS.label;
    context.font = "500 12px system-ui, sans-serif";
    context.textBaseline = "middle";
    context.fillText(text, x + 14, y);
    context.restore();
  }

  function drawScene(canvas, map, options, photo, movingPiece) {
    const nodes = getNodeMap(map);
    const context = prepareCanvas(canvas);
    context.save();
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.fillStyle = COLORS.background;
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.restore();
    context.fillStyle = COLORS.background;
    context.fillRect(0, 0, MAP_WIDTH, MAP_HEIGHT);

    const serverLegalMoves = options.legalMoves === undefined && options.state
      ? options.state.legal_moves
      : options.legalMoves;
    const legalMoves = toStringSet(serverLegalMoves, "legalMoves");
    const allowedStarts = toStringSet(
      options.allowedStarts || map.allowed_starts,
      "allowedStarts"
    );
    drawEdges(context, map, nodes, options.showDistances);
    map.nodes.forEach(function (node) {
      drawNode(context, node, map, options, legalMoves, allowedStarts);
    });
    drawPieces(context, options.state, nodes, photo, movingPiece, map);
    drawLegend(context, options, map);
  }

  function toStringSet(values, name) {
    if (values === undefined || values === null) return new Set();
    if (!Array.isArray(values) || values.some(function (value) {
      return typeof value !== "string";
    })) {
      throw new TypeError(name + " must be an array of node ids");
    }
    return new Set(values);
  }

  async function render(canvas, map, options) {
    activeCanvas = canvas;
    activeMap = map;
    activeOptions = options || {};

    const settings = activeOptions;
    const photo = await loadProctorPhoto(
      settings.proctorPhoto || "/assets/proctor.jpeg",
      settings.onPhotoError
    );
    drawScene(canvas, map, settings, photo, null);
  }

  function setStudentState(name) {
    if (["avg", "scared", "lose", "win"].includes(name)) {
      currentStudentState = name;
      if (activeCanvas && activeMap) {
        render(activeCanvas, activeMap, activeOptions);
      }
    }
  }

  async function animateMove(canvas, map, from, to, piece, options) {
    if (piece !== "student" && piece !== "proctor") {
      throw new TypeError("Animated piece must be 'student' or 'proctor'");
    }
    const nodes = getNodeMap(map);
    if (!nodes.has(from) || !nodes.has(to)) {
      throw new Error("Animated move references an unknown node");
    }

    const settings = options || {};
    const photo = await loadProctorPhoto(
      settings.proctorPhoto || "/assets/proctor.jpeg",
      settings.onPhotoError
    );
    const duration = Math.max(0, settings.duration || 500);
    const startTime = await new Promise(function (resolve) {
      global.requestAnimationFrame(resolve);
    });

    await new Promise(function (resolve) {
      function frame(timestamp) {
        const linearProgress = duration === 0
          ? 1
          : Math.min(1, (timestamp - startTime) / duration);
        const progress = linearProgress * linearProgress * (3 - 2 * linearProgress);
        drawScene(canvas, map, settings, photo, {
          piece: piece,
          from: from,
          to: to,
          progress: progress
        });
        if (linearProgress < 1) {
          global.requestAnimationFrame(frame);
        } else {
          resolve();
        }
      }
      global.requestAnimationFrame(frame);
    });
  }

  const renderer = {
    SCARED_DISTANCE: SCARED_DISTANCE,
    render: render,
    animateMove: animateMove,
    setStudentState: setStudentState,
    hopDistance: hopDistance
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = renderer;
  } else {
    global.CampusMapRenderer = renderer;
  }
})(typeof window === "undefined" ? globalThis : window);

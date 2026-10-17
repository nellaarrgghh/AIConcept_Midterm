(function (global) {
  "use strict";

  const MAP_WIDTH = 1000;
  const MAP_HEIGHT = 700;
  const GOAL_ID = "informatics";
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
    if (!photo) return Promise.resolve(null);
    if (typeof photo !== "string") {
      if (photo.complete && photo.naturalWidth > 0) {
        return Promise.resolve(photo);
      }
      if (photo.complete) {
        if (onPhotoError) onPhotoError(new Error("Proctor photo could not be loaded"));
        return Promise.resolve(null);
      }
      return new Promise(function (resolve) {
        photo.addEventListener("load", function () {
          resolve(photo);
        }, { once: true });
        photo.addEventListener("error", function (event) {
          if (onPhotoError) onPhotoError(event);
          resolve(null);
        }, { once: true });
      });
    }

    return new Promise(function (resolve) {
      const image = new global.Image();
      image.onload = function () {
        resolve(image);
      };
      image.onerror = function (event) {
        if (onPhotoError) onPhotoError(event);
        resolve(null);
      };
      image.src = photo;
    });
  }

  function drawEdges(context, map, nodes) {
    context.save();
    context.strokeStyle = COLORS.road;
    context.lineWidth = 3;
    context.lineCap = "round";
    context.beginPath();
    map.edges.forEach(function (edge) {
      if (!edge || typeof edge.from !== "string" || typeof edge.to !== "string") {
        throw new TypeError("Map edges must have from and to node ids");
      }
      const from = nodes.get(edge.from);
      const to = nodes.get(edge.to);
      if (!from || !to) {
        throw new Error("Map edge references an unknown node");
      }
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
    });
    context.stroke();
    context.restore();
  }

  function drawNode(context, node, map, options, legalMoves, allowedStarts) {
    const isGoal = node.id === (map.goal || GOAL_ID);
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

    const label = node.label || (options.showAllLabels ? node.name : null);
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
    if (piece === "proctor" && photo) {
      const radius = 20;
      context.save();
      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.clip();
      context.drawImage(photo, x - radius, y - radius, radius * 2, radius * 2);
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

    const radius = piece === "proctor" ? 20 : 14;
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

  function drawPieces(context, state, nodes, photo, movingPiece) {
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
      const x = from.x + (to.x - from.x) * progress;
      const y = from.y + (to.y - from.y) * progress;
      drawPiece(
        context,
        x,
        y,
        movingPiece.piece,
        movingPiece.piece === "proctor" ? photo : null
      );
    }
  }

  function drawLegend(context, options) {
    if (options.showLegend === false) return;
    const width = 202;
    const height = options.choosingStart ? 112 : 92;
    const x = MAP_WIDTH - width - 18;
    const y = MAP_HEIGHT - height - 18;

    context.save();
    context.fillStyle = "rgba(255, 255, 255, 0.94)";
    context.strokeStyle = "#d3ddd7";
    context.lineWidth = 1;
    context.beginPath();
    context.roundRect(x, y, width, height, 10);
    context.fill();
    context.stroke();

    drawLegendDot(context, x + 15, y + 17, COLORS.student);
    drawLegendText(context, "Student", x + 30, y + 17);
    drawLegendDot(context, x + 15, y + 38, COLORS.proctor);
    drawLegendText(context, "Proctor", x + 30, y + 38);
    drawLegendDot(context, x + 15, y + 55, COLORS.goal);
    drawLegendText(context, "Goal: Informatics", x + 30, y + 55);
    context.beginPath();
    context.arc(x + 15, y + 75, 7, 0, Math.PI * 2);
    context.lineWidth = 2;
    context.strokeStyle = COLORS.legal;
    context.stroke();
    drawLegendText(context, "Server legal move", x + 30, y + 75);
    if (options.choosingStart) {
      context.beginPath();
      context.arc(x + 15, y + 95, 6, 0, Math.PI * 2);
      context.setLineDash([3, 2]);
      context.lineWidth = 2;
      context.strokeStyle = COLORS.start;
      context.stroke();
      context.setLineDash([]);
      drawLegendText(context, "Available start", x + 30, y + 95);
    }
    context.restore();
  }

  function drawLegendDot(context, x, y, color) {
    context.beginPath();
    context.arc(x, y, 6, 0, Math.PI * 2);
    context.fillStyle = color;
    context.fill();
  }

  function drawLegendText(context, text, x, y) {
    context.fillStyle = COLORS.label;
    context.font = "500 12px system-ui, sans-serif";
    context.textBaseline = "middle";
    context.fillText(text, x, y);
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

    // Legal moves come from the API; the renderer never derives them from edges.
    const serverLegalMoves = options.legalMoves === undefined && options.state
      ? options.state.legal_moves
      : options.legalMoves;
    const legalMoves = toStringSet(serverLegalMoves, "legalMoves");
    const allowedStarts = toStringSet(
      options.allowedStarts || map.allowed_starts,
      "allowedStarts"
    );
    drawEdges(context, map, nodes);
    map.nodes.forEach(function (node) {
      drawNode(context, node, map, options, legalMoves, allowedStarts);
    });
    drawPieces(context, options.state, nodes, photo, movingPiece);
    drawLegend(context, options);
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
    const settings = options || {};
    const photo = await loadProctorPhoto(
      settings.proctorPhoto,
      settings.onPhotoError
    );
    drawScene(canvas, map, settings, photo, null);
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
      settings.proctorPhoto,
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
    render: render,
    animateMove: animateMove
  };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = renderer;
  } else {
    global.CampusMapRenderer = renderer;
  }
})(typeof window === "undefined" ? globalThis : window);

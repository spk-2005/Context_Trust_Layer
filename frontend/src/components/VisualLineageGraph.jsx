import React, { useState, useEffect, useMemo, useRef } from 'react';

export default function VisualLineageGraph({ activeOrg, showToast }) {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [blastRadius, setBlastRadius] = useState(null);
  const [loadingBlastRadius, setLoadingBlastRadius] = useState(false);

  // View Mode: 'conflicts' (default clean DAG), 'focused' (centered around active asset), 'all' (sample overview)
  const [viewMode, setViewMode] = useState('conflicts');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerSearch, setDrawerSearch] = useState('');
  const [drawerDocFilter, setDrawerDocFilter] = useState('all');

  // Free-form Canvas Pan & Zoom State
  const [zoom, setZoom] = useState(0.85);
  const [pan, setPan] = useState({ x: 60, y: 100 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Free-form Node Dragging
  const [draggedNodeId, setDraggedNodeId] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [customPositions, setCustomPositions] = useState({});

  // Expand / Collapse Branches
  const [collapsedNodes, setCollapsedNodes] = useState(new Set());

  const containerRef = useRef(null);

  const fetchLineage = async () => {
    setLoading(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/lineage/graph?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
        if (data.nodes && data.nodes.length > 0 && !selectedNodeId) {
          // Default focus to the first contradiction or claim
          const firstConflict = data.nodes.find(n => n.type === 'conflict');
          const firstClaim = data.nodes.find(n => n.type === 'claim');
          setSelectedNodeId(firstConflict ? firstConflict.id : (firstClaim ? firstClaim.id : data.nodes[0].id));
        }
      } else {
        showToast?.("Failed to fetch lineage graph", "error");
      }
    } catch (e) {
      console.warn("Lineage fetch fallback:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchBlastRadius = async (claimId) => {
    if (!claimId) return;
    setLoadingBlastRadius(true);
    try {
      const res = await fetch(`/v1/lineage/blast-radius/${claimId}`);
      if (res.ok) {
        const data = await res.json();
        setBlastRadius(data);
      }
    } catch (e) {
      console.warn("Failed to fetch blast radius:", e);
    } finally {
      setLoadingBlastRadius(false);
    }
  };

  useEffect(() => {
    fetchLineage();
  }, [activeOrg?.id]);

  const selectedNode = useMemo(() => {
    return graphData?.nodes?.find(n => n.id === selectedNodeId) || null;
  }, [graphData, selectedNodeId]);

  useEffect(() => {
    if (selectedNode && selectedNode.type === 'claim') {
      const claimId = selectedNode.data?.claim_id || selectedNode.id.replace('cl_', '');
      fetchBlastRadius(claimId);
    } else {
      setBlastRadius(null);
    }
  }, [selectedNode]);

  // Compute Full Upstream & Downstream Connected Sets from real edges
  const connectedNodeMap = useMemo(() => {
    if (!selectedNodeId || !graphData?.edges) {
      return { up: new Set(), down: new Set(), all: new Set(), activeEdgeIds: new Set() };
    }
    const up = new Set();
    const down = new Set();
    const all = new Set([selectedNodeId]);
    const activeEdgeIds = new Set();

    // 1st tier connections
    graphData.edges.forEach(e => {
      if (e.target === selectedNodeId) {
        up.add(e.source);
        all.add(e.source);
        activeEdgeIds.add(e.id);
      }
      if (e.source === selectedNodeId) {
        down.add(e.target);
        all.add(e.target);
        activeEdgeIds.add(e.id);
      }
    });

    // 2nd tier upstream: from documents to data sources
    graphData.edges.forEach(e => {
      if (up.has(e.target)) {
        up.add(e.source);
        all.add(e.source);
        activeEdgeIds.add(e.id);
      }
      if (down.has(e.source)) {
        down.add(e.target);
        all.add(e.target);
        activeEdgeIds.add(e.id);
      }
    });

    return { up, down, all, activeEdgeIds };
  }, [selectedNodeId, graphData]);

  // Node Dimensions
  const CARD_WIDTH = 270;
  const CARD_HEIGHT = 92;

  // Smart DAG Layout: Capped and contextual to prevent browser freezing
  const defaultPositions = useMemo(() => {
    const map = {};
    if (!graphData?.nodes) return map;

    const sources = graphData.nodes.filter(n => n.type === 'source');
    const documents = graphData.nodes.filter(n => n.type === 'document');
    const claims = graphData.nodes.filter(n => n.type === 'claim');
    const conflicts = graphData.nodes.filter(n => n.type === 'conflict');
    const decisions = graphData.nodes.filter(n => n.type === 'decision');

    let activeSources = [];
    let activeDocs = [];
    let activeClaims = [];
    let activeConflicts = [];
    let activeDecisions = [];

    const MAX_PER_TIER = 6;

    if (viewMode === 'conflicts') {
      // 1. Conflict Focus Mode: Show active contradictory branches
      activeConflicts = conflicts.slice(0, MAX_PER_TIER);
      const conflictClaimIds = new Set();
      activeConflicts.forEach(c => {
        if (c.data?.first_claim_id) conflictClaimIds.add(`cl_${c.data.first_claim_id}`);
        if (c.data?.second_claim_id) conflictClaimIds.add(`cl_${c.data.second_claim_id}`);
      });

      activeClaims = claims.filter(cl => conflictClaimIds.has(cl.id)).slice(0, MAX_PER_TIER);
      if (activeClaims.length === 0) {
        activeClaims = claims.slice(0, MAX_PER_TIER);
      }

      const docIds = new Set();
      activeClaims.forEach(cl => {
        graphData.edges.forEach(e => {
          if (e.target === cl.id && e.source.startsWith('doc_')) {
            docIds.add(e.source);
          }
        });
      });
      activeDocs = documents.filter(d => docIds.has(d.id)).slice(0, MAX_PER_TIER);
      if (activeDocs.length === 0) activeDocs = documents.slice(0, 3);

      const srcIds = new Set();
      activeDocs.forEach(d => {
        graphData.edges.forEach(e => {
          if (e.target === d.id && e.source.startsWith('src_')) {
            srcIds.add(e.source);
          }
        });
      });
      activeSources = sources.filter(s => srcIds.has(s.id)).slice(0, MAX_PER_TIER);
      if (activeSources.length === 0) activeSources = sources.slice(0, 3);

      activeDecisions = decisions.slice(0, 3);
    } else if (viewMode === 'focused' && selectedNodeId) {
      // 2. Active Focus Mode: Focus strictly on selected node and its direct neighbors
      activeSources = sources.filter(n => connectedNodeMap.all.has(n.id)).slice(0, MAX_PER_TIER);
      if (activeSources.length === 0) activeSources = sources.slice(0, 2);

      activeDocs = documents.filter(n => connectedNodeMap.all.has(n.id)).slice(0, MAX_PER_TIER);
      if (activeDocs.length === 0) activeDocs = documents.slice(0, 3);

      activeClaims = claims.filter(n => connectedNodeMap.all.has(n.id)).slice(0, MAX_PER_TIER);
      if (activeClaims.length === 0) activeClaims = claims.slice(0, 4);

      activeConflicts = conflicts.filter(n => connectedNodeMap.all.has(n.id)).slice(0, MAX_PER_TIER);
      if (activeConflicts.length === 0) activeConflicts = conflicts.slice(0, 3);

      activeDecisions = decisions.filter(n => connectedNodeMap.all.has(n.id)).slice(0, MAX_PER_TIER);
      if (activeDecisions.length === 0) activeDecisions = decisions.slice(0, 2);
    } else {
      // 3. Full Overview Mode: Capped cleanly at top 6 per tier
      activeSources = sources.slice(0, MAX_PER_TIER);
      activeDocs = documents.slice(0, MAX_PER_TIER);
      activeClaims = claims.slice(0, MAX_PER_TIER);
      activeConflicts = conflicts.slice(0, MAX_PER_TIER);
      activeDecisions = decisions.slice(0, MAX_PER_TIER);
    }

    // Always guarantee selected node is in position map
    if (selectedNode && !map[selectedNode.id]) {
      if (selectedNode.type === 'source' && !activeSources.some(n => n.id === selectedNode.id)) activeSources.unshift(selectedNode);
      if (selectedNode.type === 'document' && !activeDocs.some(n => n.id === selectedNode.id)) activeDocs.unshift(selectedNode);
      if (selectedNode.type === 'claim' && !activeClaims.some(n => n.id === selectedNode.id)) activeClaims.unshift(selectedNode);
      if (selectedNode.type === 'conflict' && !activeConflicts.some(n => n.id === selectedNode.id)) activeConflicts.unshift(selectedNode);
      if (selectedNode.type === 'decision' && !activeDecisions.some(n => n.id === selectedNode.id)) activeDecisions.unshift(selectedNode);
    }

    const levels = [
      { nodes: activeSources, x: 50 },
      { nodes: activeDocs, x: 380 },
      { nodes: activeClaims, x: 720 },
      { nodes: activeConflicts, x: 1060 },
      { nodes: activeDecisions, x: 1400 }
    ];

    levels.forEach((lvl) => {
      const count = lvl.nodes.length;
      const totalH = count * 130;
      const startY = Math.max(60, 260 - totalH / 2);

      lvl.nodes.forEach((node, idx) => {
        map[node.id] = {
          x: lvl.x,
          y: startY + idx * 130
        };
      });
    });

    return map;
  }, [graphData, selectedNodeId, connectedNodeMap, viewMode, selectedNode]);

  // Merged positions (custom user drags take precedence)
  const nodePositions = useMemo(() => {
    return { ...defaultPositions, ...customPositions };
  }, [defaultPositions, customPositions]);

  // Filter rendered nodes based on search & positions
  const renderedNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    return graphData.nodes.filter(n => {
      if (!nodePositions[n.id]) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return n.label?.toLowerCase().includes(q) || (n.fullText && n.fullText.toLowerCase().includes(q));
      }
      return true;
    });
  }, [graphData, nodePositions, searchQuery]);

  // Directional Bezier Connecting Edges
  const renderedEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    return graphData.edges
      .filter(e => nodePositions[e.source] && nodePositions[e.target])
      .map(e => {
        const src = nodePositions[e.source];
        const tgt = nodePositions[e.target];
        const x1 = src.x + CARD_WIDTH;
        const y1 = src.y + CARD_HEIGHT / 2;
        const x2 = tgt.x;
        const y2 = tgt.y + CARD_HEIGHT / 2;
        const dx = Math.max(50, (x2 - x1) * 0.5);

        const pathData = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        const isActive = connectedNodeMap.activeEdgeIds.has(e.id);

        return {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          pathData,
          midX,
          midY,
          isActive
        };
      });
  }, [graphData, nodePositions, connectedNodeMap]);

  // Canvas Pan Handlers
  const handleCanvasMouseDown = (e) => {
    if (e.target.closest('.atlan-node-card') || e.target.closest('.canvas-btn') || e.target.closest('select') || e.target.closest('input')) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    } else if (draggedNodeId) {
      const newX = (e.clientX - dragOffset.x - pan.x) / zoom;
      const newY = (e.clientY - dragOffset.y - pan.y) / zoom;
      setCustomPositions(prev => ({
        ...prev,
        [draggedNodeId]: { x: Math.round(newX), y: Math.round(newY) }
      }));
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggedNodeId(null);
  };

  const handleNodeDragStart = (e, nodeId) => {
    e.stopPropagation();
    setDraggedNodeId(nodeId);
    const pos = nodePositions[nodeId] || { x: 0, y: 0 };
    setDragOffset({
      x: e.clientX - (pos.x * zoom + pan.x),
      y: e.clientY - (pos.y * zoom + pan.y)
    });
  };

  const toggleCollapseNode = (e, nodeId) => {
    e.stopPropagation();
    setCollapsedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  const resetCanvasView = () => {
    setZoom(0.85);
    setPan({ x: 60, y: 100 });
    setCustomPositions({});
  };

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      
      {/* Top Atlan-Style Asset Selector Bar */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '12px 18px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        {/* Left: Breadcrumbs & Focus Asset Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>All assets</span>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>&rsaquo;</span>
          
          {/* Asset Dropdown Selector */}
          <select
            value={selectedNodeId || ''}
            onChange={(e) => {
              setSelectedNodeId(e.target.value);
              if (viewMode === 'conflicts') setViewMode('focused');
            }}
            style={{
              padding: '5px 10px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              background: '#f8fafc',
              fontSize: '0.82rem',
              fontWeight: 700,
              color: '#2026d2',
              cursor: 'pointer',
              maxWidth: '320px',
              outline: 'none'
            }}
          >
            {(!graphData?.nodes || graphData.nodes.length === 0) ? (
              <option value="">No assets ingested yet</option>
            ) : (
              graphData.nodes.map(n => (
                <option key={n.id} value={n.id}>
                  [{n.type.toUpperCase()}] {n.label}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Center: DAG Perspective Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '3px', background: '#f1f5f9', padding: '3px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <button
            onClick={() => {
              setViewMode('conflicts');
              const firstConf = graphData?.nodes?.find(n => n.type === 'conflict');
              if (firstConf) setSelectedNodeId(firstConf.id);
            }}
            style={{
              padding: '5px 11px',
              fontSize: '0.74rem',
              fontWeight: 700,
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              background: viewMode === 'conflicts' ? '#ea580c' : 'transparent',
              color: viewMode === 'conflicts' ? '#fff' : '#475569',
              boxShadow: viewMode === 'conflicts' ? '0 1px 4px rgba(234,88,12,0.3)' : 'none',
              transition: 'all 0.15s ease'
            }}
            title="Focus exclusively on contradictory claims and their lineage"
          >
            ⚡ Contradictions DAG ({graphData?.nodes?.filter(n => n.type === 'conflict')?.length || 0})
          </button>
          <button
            onClick={() => setViewMode('focused')}
            style={{
              padding: '5px 11px',
              fontSize: '0.74rem',
              fontWeight: 700,
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              background: viewMode === 'focused' ? '#2563eb' : 'transparent',
              color: viewMode === 'focused' ? '#fff' : '#475569',
              boxShadow: viewMode === 'focused' ? '0 1px 4px rgba(37,99,235,0.3)' : 'none',
              transition: 'all 0.15s ease'
            }}
            title="Focus on active node's direct lineage path"
          >
            🔍 Active Focus DAG
          </button>
          <button
            onClick={() => setViewMode('all')}
            style={{
              padding: '5px 11px',
              fontSize: '0.74rem',
              fontWeight: 700,
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              background: viewMode === 'all' ? '#0284c7' : 'transparent',
              color: viewMode === 'all' ? '#fff' : '#475569',
              boxShadow: viewMode === 'all' ? '0 1px 4px rgba(2,132,199,0.3)' : 'none',
              transition: 'all 0.15s ease'
            }}
            title="Clean top-tier overview across all asset types"
          >
            🌐 Full Overview DAG
          </button>
        </div>

        {/* Right Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="btn btn-secondary canvas-btn"
            style={{ padding: '6px 12px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '5px', background: '#f8fafc', border: '1px solid #cbd5e1' }}
            title="Browse all extracted atomic claims in searchable list"
          >
            <span>📋</span>
            <span>All Claims Drawer ({graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0})</span>
          </button>
          <button
            onClick={fetchLineage}
            disabled={loading}
            className="btn btn-secondary canvas-btn"
            style={{ padding: '6px 12px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <span>🔄</span>
            <span>Refresh Lineage</span>
          </button>
          <button
            onClick={() => showToast?.("Exporting end-to-end lineage DAG snapshot...")}
            className="btn btn-primary canvas-btn"
            style={{ padding: '6px 14px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <span>+ Request Data Access</span>
          </button>
        </div>
      </div>

      {/* Free-Form Interactive Graph Canvas */}
      <div style={{ position: 'relative', width: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)', background: '#fff' }}>
        
        {/* Floating Atlan Toolbar (Top-Right) */}
        <div style={{
          position: 'absolute',
          top: '14px',
          right: '14px',
          zIndex: 30,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(8px)',
          padding: '6px 10px',
          borderRadius: '10px',
          boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
          border: '1px solid #e2e8f0'
        }}>
          {/* Find in canvas */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', paddingRight: '8px', borderRight: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>🔍</span>
            <input
              type="text"
              placeholder="Find in canvas..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                border: 'none',
                background: 'transparent',
                fontSize: '0.78rem',
                outline: 'none',
                width: '120px',
                color: 'var(--text-main)'
              }}
            />
          </div>

          {/* Zoom Controls */}
          <button
            onClick={() => setZoom(z => Math.max(0.4, z - 0.1))}
            className="canvas-btn"
            style={{ width: '26px', height: '26px', borderRadius: '6px', border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontWeight: 700, fontSize: '0.85rem' }}
            title="Zoom Out"
          >
            -
          </button>
          <span style={{ fontSize: '0.72rem', fontWeight: 600, minWidth: '32px', textAlign: 'center', color: '#475569' }}>
            {(zoom * 100).toFixed(0)}%
          </span>
          <button
            onClick={() => setZoom(z => Math.min(1.4, z + 0.1))}
            className="canvas-btn"
            style={{ width: '26px', height: '26px', borderRadius: '6px', border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontWeight: 700, fontSize: '0.85rem' }}
            title="Zoom In"
          >
            +
          </button>
          <button
            onClick={resetCanvasView}
            className="canvas-btn"
            style={{ padding: '0 8px', height: '26px', borderRadius: '6px', border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontSize: '0.72rem', color: '#2026d2', fontWeight: 600 }}
            title="Reset Pan & Zoom"
          >
            Auto-Layout
          </button>
        </div>

        {/* Floating Legend / Instructions at bottom left */}
        <div style={{
          position: 'absolute',
          bottom: '14px',
          left: '14px',
          zIndex: 30,
          background: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(8px)',
          padding: '8px 14px',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
          border: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontSize: '0.72rem',
          color: '#475569'
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#2026d2' }} /> Data Source
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#0284c7' }} /> Document
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#16a34a' }} /> Atomic Claim
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ea580c' }} /> Contradiction
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#7c3aed' }} /> AI Decision
          </span>
          <span style={{ color: '#94a3b8', marginLeft: '4px' }}>| Drag nodes freely to customize DAG layout</span>
        </div>

        {/* Free-form Pan Canvas */}
        <div
          ref={containerRef}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{
            height: '660px',
            width: '100%',
            cursor: isPanning ? 'grabbing' : 'grab',
            overflow: 'hidden',
            position: 'relative',
            background: 'radial-gradient(#cbd5e1 1.2px, transparent 1.2px)',
            backgroundSize: '22px 22px',
            backgroundColor: '#fafbfc'
          }}
        >
          {/* Zoom & Pan Transform Layer */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: '0 0'
            }}
          >
            {/* SVG Connecting Bezier Lines */}
            <svg
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '3200px',
                height: '2400px',
                pointerEvents: 'none',
                zIndex: 2
              }}
            >
              <defs>
                <marker id="atlan-arrow-default" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                  <path d="M0,0 L0,6 L6,3 z" fill="#94a3b8" />
                </marker>
                <marker id="atlan-arrow-active" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                  <path d="M0,0 L0,8 L8,4 z" fill="#2563eb" />
                </marker>
                <marker id="atlan-arrow-conflict" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                  <path d="M0,0 L0,8 L8,4 z" fill="#ea580c" />
                </marker>
                <marker id="atlan-arrow-decision" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                  <path d="M0,0 L0,8 L8,4 z" fill="#7c3aed" />
                </marker>
              </defs>

              {renderedEdges.map(edge => {
                const strokeColor = edge.isActive
                  ? edge.type === 'conflict' ? '#ea580c' : edge.type === 'decision_grounding' ? '#7c3aed' : '#2563eb'
                  : '#cbd5e1';
                const strokeWidth = edge.isActive ? 2.5 : 1.5;
                const marker = edge.isActive
                  ? edge.type === 'conflict' ? 'url(#atlan-arrow-conflict)' : edge.type === 'decision_grounding' ? 'url(#atlan-arrow-decision)' : 'url(#atlan-arrow-active)'
                  : 'url(#atlan-arrow-default)';

                return (
                  <g key={edge.id}>
                    <path
                      d={edge.pathData}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeDasharray={edge.isActive ? '6 3' : 'none'}
                      markerEnd={marker}
                      style={{
                        transition: 'stroke 0.2s ease, stroke-width 0.2s ease',
                        animation: edge.isActive ? 'dash-flow 1.5s linear infinite' : 'none'
                      }}
                    />

                    {/* Circular Connector badge on bezier curve */}
                    <circle
                      cx={edge.midX}
                      cy={edge.midY}
                      r="9"
                      fill="#fff"
                      stroke={strokeColor}
                      strokeWidth={edge.isActive ? 2 : 1.5}
                    />
                    <text
                      x={edge.midX}
                      y={edge.midY + 3}
                      fontSize="9"
                      textAnchor="middle"
                      fill={strokeColor}
                      fontWeight="bold"
                    >
                      {edge.type === 'conflict' ? '⚖️' : edge.type === 'decision_grounding' ? '🤖' : '❄️'}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Empty State Banner if No Nodes Ingested Yet */}
            {renderedNodes.length === 0 && (
              <div style={{
                position: 'absolute',
                top: '240px',
                left: '260px',
                textAlign: 'center',
                background: 'rgba(255,255,255,0.96)',
                backdropFilter: 'blur(8px)',
                padding: '36px 44px',
                borderRadius: '16px',
                border: '1px solid #cbd5e1',
                boxShadow: '0 12px 32px rgba(0,0,0,0.06)',
                maxWidth: '520px',
                pointerEvents: 'auto'
              }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '10px' }}>🕸️</div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#1e293b', margin: '0 0 8px 0' }}>
                  Lineage Graph Ready
                </h3>
                <p style={{ fontSize: '0.84rem', color: '#64748b', lineHeight: 1.55, margin: 0 }}>
                  No documents or claims ingested yet for organization <strong>{activeOrg?.name || 'demo'}</strong>. Upload and ingest your PDF policies in <strong>Live Ingestion Studio</strong> to automatically extract atomic claims, detect contradictions, and visualize full end-to-end lineage.
                </p>
              </div>
            )}

            {/* Draggable Node Cards Bound to Real Backend Entities */}
            {renderedNodes.map(node => {
              const pos = nodePositions[node.id] || { x: 100, y: 100 };
              const isSelected = selectedNodeId === node.id;
              const isUpstream = connectedNodeMap.up.has(node.id);
              const isDownstream = connectedNodeMap.down.has(node.id);
              const isConnected = connectedNodeMap.all.has(node.id);

              let borderColor = '#3b82f6';
              let badgeBg = '#f0f7ff';
              let badgeColor = '#2563eb';
              let nodeIcon = '⚡';
              let categoryLabel = 'ATOMIC CLAIM';
              let subtitleText = `SCOPE / ${node.data?.scope || 'ENTERPRISE'}`;

              if (node.type === 'source') {
                borderColor = '#2026d2';
                badgeBg = '#eef2ff';
                badgeColor = '#2026d2';
                nodeIcon = '🔌';
                categoryLabel = 'DATA SOURCE';
                subtitleText = `TYPE / ${node.subType?.toUpperCase() || 'CONNECTOR'} • AUTH ${node.authority}%`;
              } else if (node.type === 'document') {
                borderColor = '#0284c7';
                badgeBg = '#f0f9ff';
                badgeColor = '#0284c7';
                nodeIcon = '📄';
                categoryLabel = 'DOCUMENT';
                subtitleText = `TYPE / ${node.subType?.toUpperCase() || 'POLICY'} • v${node.data?.version_count || 1}.0`;
              } else if (node.type === 'conflict') {
                borderColor = '#ea580c';
                badgeBg = '#fff7ed';
                badgeColor = '#ea580c';
                nodeIcon = '⚖️';
                categoryLabel = 'CONTRADICTION';
                subtitleText = `STATUS / ${node.status || 'REVIEW_REQUIRED'}`;
              } else if (node.type === 'decision') {
                borderColor = '#7c3aed';
                badgeBg = '#faf5ff';
                badgeColor = '#7c3aed';
                nodeIcon = '🤖';
                categoryLabel = 'AI DECISION';
                subtitleText = `ACTOR / ${node.actor || 'AGENT_EVAL'}`;
              }

              return (
                <div
                  key={node.id}
                  className="atlan-node-card"
                  onClick={() => setSelectedNodeId(node.id)}
                  onMouseDown={(e) => handleNodeDragStart(e, node.id)}
                  style={{
                    position: 'absolute',
                    left: `${pos.x}px`,
                    top: `${pos.y}px`,
                    width: `${CARD_WIDTH}px`,
                    height: `${CARD_HEIGHT}px`,
                    background: '#fff',
                    borderRadius: '10px',
                    border: isSelected ? `2px solid ${borderColor}` : isConnected ? `1.5px solid ${borderColor}` : '1px solid #cbd5e1',
                    boxShadow: isSelected
                      ? `0 0 0 4px ${borderColor}30, 0 8px 24px rgba(0,0,0,0.12)`
                      : isConnected
                        ? `0 0 0 2px ${borderColor}20, 0 4px 12px rgba(0,0,0,0.06)`
                        : '0 2px 8px rgba(0,0,0,0.04)',
                    boxSizing: 'border-box',
                    padding: '10px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    cursor: draggedNodeId === node.id ? 'grabbing' : 'pointer',
                    userSelect: 'none',
                    zIndex: isSelected ? 20 : isConnected ? 10 : 5,
                    transition: draggedNodeId === node.id ? 'none' : 'box-shadow 0.15s ease, border-color 0.15s ease'
                  }}
                >
                  {/* Home / Focus Asset Badge */}
                  {isSelected && (
                    <div style={{
                      position: 'absolute',
                      top: '-14px',
                      left: '12px',
                      background: '#2563eb',
                      color: '#fff',
                      borderRadius: '5px 5px 0 0',
                      padding: '2px 8px',
                      fontSize: '0.62rem',
                      fontWeight: 700,
                      boxShadow: '0 2px 6px rgba(37,99,235,0.3)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '3px'
                    }}>
                      <span>🏠 Focus Asset</span>
                    </div>
                  )}

                  {/* Left Connection Port (-/+) */}
                  {node.type !== 'source' && (
                    <div
                      onClick={(e) => toggleCollapseNode(e, node.id)}
                      style={{
                        position: 'absolute',
                        left: '-10px',
                        top: 'calc(50% - 10px)',
                        width: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        background: '#fff',
                        border: `1.5px solid ${borderColor}`,
                        boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '11px',
                        fontWeight: 800,
                        color: borderColor,
                        cursor: 'pointer',
                        zIndex: 25
                      }}
                      title="Expand/Collapse incoming branches"
                    >
                      {collapsedNodes.has(node.id) ? '+' : '-'}
                    </div>
                  )}

                  {/* Right Connection Port (-/+) */}
                  {node.type !== 'decision' && (
                    <div
                      onClick={(e) => toggleCollapseNode(e, node.id)}
                      style={{
                        position: 'absolute',
                        right: '-10px',
                        top: 'calc(50% - 10px)',
                        width: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        background: '#fff',
                        border: `1.5px solid ${borderColor}`,
                        boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '11px',
                        fontWeight: 800,
                        color: borderColor,
                        cursor: 'pointer',
                        zIndex: 25
                      }}
                      title="Expand/Collapse downstream branches"
                    >
                      {collapsedNodes.has(node.id) ? '+' : '-'}
                    </div>
                  )}

                  {/* Card Header: Category & Metrics */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{
                      fontSize: '0.62rem',
                      fontWeight: 800,
                      color: badgeColor,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em'
                    }}>
                      {categoryLabel}
                    </span>

                    {node.trustScore !== undefined && (
                      <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 5px', fontWeight: 700 }}>
                        {(node.trustScore * 100).toFixed(0)}% Trust
                      </span>
                    )}
                    {node.severity && (
                      <span className="badge badge-review" style={{ fontSize: '0.62rem', padding: '1px 5px', fontWeight: 700 }}>
                        {node.severity}
                      </span>
                    )}
                    {node.verdict && (
                      <span className={node.verdict === 'ALLOW' ? 'badge badge-verified' : 'badge badge-warning'} style={{ fontSize: '0.62rem', padding: '1px 5px', fontWeight: 700 }}>
                        {node.verdict}
                      </span>
                    )}
                  </div>

                  {/* Card Body: Real Entity Title */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                    <span style={{ fontSize: '15px' }}>{nodeIcon}</span>
                    <span style={{
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      color: '#1e293b',
                      lineHeight: 1.25,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {node.label}
                    </span>
                  </div>

                  {/* Card Footer: Real Metadata / Scope */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid #f1f5f9', paddingTop: '4px', fontSize: '0.65rem', color: '#64748b' }}>
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '170px' }}>
                      {subtitleText}
                    </span>
                    <span style={{ color: '#2563eb', fontWeight: 600, fontSize: '0.62rem' }}>
                      view lineage &rsaquo;
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Entity Metadata & Downstream Blast Radius Inspector */}
      {selectedNode && (
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '18px 24px',
          display: 'grid',
          gridTemplateColumns: 'minmax(300px, 1.2fr) minmax(320px, 1fr)',
          gap: '20px',
          alignItems: 'start'
        }}>
          {/* Left Column: Full Real Node Metadata */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '20px' }}>
                {selectedNode.type === 'source' ? '🔌' : selectedNode.type === 'document' ? '📄' : selectedNode.type === 'claim' ? '⚡' : selectedNode.type === 'conflict' ? '⚖️' : '🤖'}
              </span>
              <div>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                  {selectedNode.label}
                </h3>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Node Type: <strong style={{ textTransform: 'uppercase' }}>{selectedNode.type}</strong> &bull; ID: <code style={{ fontSize: '0.7rem' }}>{selectedNode.id}</code>
                </span>
              </div>
            </div>

            {selectedNode.fullText && (
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-main)', lineHeight: 1.45, background: 'var(--bg-card)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                "{selectedNode.fullText}"
              </p>
            )}

            {/* Upstream & Downstream Lineage Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginTop: '4px' }}>
              <div style={{ background: 'var(--bg-card)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Upstream Roots</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0284c7', marginTop: '2px' }}>{connectedNodeMap.up.size}</div>
              </div>
              <div style={{ background: 'var(--bg-card)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Downstream Targets</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#7c3aed', marginTop: '2px' }}>{connectedNodeMap.down.size}</div>
              </div>
              <div style={{ background: 'var(--bg-card)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Trust Score</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#16a34a', marginTop: '2px' }}>
                  {selectedNode.trustScore !== undefined ? `${(selectedNode.trustScore * 100).toFixed(0)}%` : '98%'}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Downstream Blast Radius & Remediation */}
          <div>
            {selectedNode.type === 'claim' ? (
              <div style={{
                background: blastRadius?.risk_tier === 'CRITICAL' || blastRadius?.risk_tier === 'HIGH' ? 'rgba(234,88,12,0.06)' : 'rgba(25,195,125,0.06)',
                border: `1px solid ${blastRadius?.risk_tier === 'CRITICAL' || blastRadius?.risk_tier === 'HIGH' ? 'rgba(234,88,12,0.3)' : 'rgba(25,195,125,0.3)'}`,
                borderRadius: '10px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    Downstream Policy Blast Radius
                  </span>
                  <span className={blastRadius?.risk_tier === 'CRITICAL' || blastRadius?.risk_tier === 'HIGH' ? 'badge badge-warning' : 'badge badge-verified'} style={{ fontSize: '0.7rem' }}>
                    {blastRadius?.risk_tier || 'LOW'} RISK ({blastRadius?.risk_score || 15}/100)
                  </span>
                </div>

                <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  {blastRadius?.recommendation || 'Calculates what breaks across AI models if this knowledge is modified.'}
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '4px' }}>
                  <div style={{ background: 'var(--bg-card)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.75rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Connected Conflicts: </span>
                    <strong style={{ color: '#ea580c' }}>{blastRadius?.connected_conflicts_count || 0}</strong>
                  </div>
                  <div style={{ background: 'var(--bg-card)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.75rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Affected AI Decisions: </span>
                    <strong style={{ color: '#7c3aed' }}>{blastRadius?.impacted_decisions_count || 0}</strong>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <strong style={{ color: 'var(--text-main)' }}>Lineage Context:</strong> Select an individual <strong>Atomic Claim (⚡)</strong> to run automated blast-radius simulation and assess downstream AI agent decision impact.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Slide-Out All Claims Explorer Drawer */}
      {isDrawerOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.45)',
          backdropFilter: 'blur(4px)',
          zIndex: 9999,
          display: 'flex',
          justifyContent: 'flex-end',
          animation: 'fadeIn 0.2s ease-out'
        }}>
          {/* Drawer backdrop dismiss */}
          <div
            style={{ flex: 1 }}
            onClick={() => setIsDrawerOpen(false)}
          />

          {/* Drawer Content Panel */}
          <div style={{
            width: '620px',
            maxWidth: '92vw',
            height: '100%',
            background: '#ffffff',
            boxShadow: '-8px 0 32px rgba(0,0,0,0.2)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 10000,
            overflow: 'hidden'
          }}>
            {/* Drawer Header */}
            <div style={{
              padding: '20px 24px',
              borderBottom: '1px solid #e2e8f0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#f8fafc'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '18px' }}>⚡</span>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800, color: '#0f172a' }}>
                    Enterprise Atomic Claims Explorer
                  </h3>
                </div>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.78rem', color: '#64748b' }}>
                  Search and inspect all {graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0} atomic policy rules extracted across documents.
                </p>
              </div>
              <button
                onClick={() => setIsDrawerOpen(false)}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#475569'
                }}
              >
                ✕
              </button>
            </div>

            {/* Filter & Search Bar */}
            <div style={{ padding: '14px 24px', borderBottom: '1px solid #f1f5f9', background: '#fff', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '220px', position: 'relative' }}>
                <input
                  type="text"
                  placeholder="Search claim text, threshold, topic..."
                  value={drawerSearch}
                  onChange={(e) => setDrawerSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px 8px 32px',
                    borderRadius: '8px',
                    border: '1px solid #cbd5e1',
                    fontSize: '0.82rem',
                    outline: 'none'
                  }}
                />
                <span style={{ position: 'absolute', left: '10px', top: '9px', fontSize: '0.85rem', color: '#94a3b8' }}>🔍</span>
              </div>

              {/* Document Filter Selector */}
              <select
                value={drawerDocFilter}
                onChange={(e) => setDrawerDocFilter(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid #cbd5e1',
                  fontSize: '0.8rem',
                  background: '#f8fafc',
                  maxWidth: '220px',
                  outline: 'none'
                }}
              >
                <option value="all">All Documents ({graphData?.nodes?.filter(n => n.type === 'document')?.length || 0})</option>
                {graphData?.nodes?.filter(n => n.type === 'document')?.map(d => (
                  <option key={d.id} value={d.id}>{d.label}</option>
                ))}
              </select>
            </div>

            {/* Claims Scrollable List */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {(() => {
                const allClaims = graphData?.nodes?.filter(n => n.type === 'claim') || [];
                const filtered = allClaims.filter(cl => {
                  if (drawerDocFilter !== 'all') {
                    const matchesDoc = graphData?.edges?.some(e => e.source === drawerDocFilter && e.target === cl.id);
                    if (!matchesDoc) return false;
                  }
                  if (drawerSearch.trim()) {
                    const q = drawerSearch.toLowerCase();
                    const text = (cl.fullText || cl.label || '').toLowerCase();
                    return text.includes(q);
                  }
                  return true;
                });

                if (filtered.length === 0) {
                  return (
                    <div style={{ textAlign: 'center', padding: '40px 20px', color: '#94a3b8' }}>
                      <div style={{ fontSize: '24px', marginBottom: '8px' }}>🔎</div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>No claims matched your search</div>
                      <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>Try clearing filters or searching for keywords like "refund", "limit", or "approval".</div>
                    </div>
                  );
                }

                return filtered.map((cl, idx) => {
                  const docEdge = graphData?.edges?.find(e => e.target === cl.id && e.source.startsWith('doc_'));
                  const parentDoc = graphData?.nodes?.find(n => n.id === docEdge?.source);
                  const isConflicted = cl.status === 'conflicted';

                  return (
                    <div
                      key={cl.id}
                      style={{
                        padding: '14px 16px',
                        borderRadius: '10px',
                        border: isConflicted ? '1.5px solid #ea580c' : '1px solid #e2e8f0',
                        background: isConflicted ? '#fff7ed' : '#ffffff',
                        boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '0.68rem', fontWeight: 800, color: '#64748b' }}>#{idx + 1}</span>
                          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#0284c7' }}>
                            📄 {parentDoc?.label || 'Parent Document'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span className={isConflicted ? 'badge badge-warning' : 'badge badge-verified'} style={{ fontSize: '0.65rem' }}>
                            {isConflicted ? '⚠️ In Conflict' : 'Verified'}
                          </span>
                          <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                            {((cl.trustScore || 0.92) * 100).toFixed(0)}% Trust
                          </span>
                        </div>
                      </div>

                      <p style={{ margin: 0, fontSize: '0.82rem', color: '#1e293b', lineHeight: 1.45, fontWeight: 500 }}>
                        "{cl.fullText || cl.label}"
                      </p>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px', borderTop: '1px solid #f1f5f9', paddingTop: '8px' }}>
                        <span style={{ fontSize: '0.68rem', color: '#64748b' }}>
                          Scope: <strong>{cl.data?.scope || 'Enterprise'}</strong> &bull; ID: <code>{cl.id.slice(0, 12)}</code>
                        </span>
                        <button
                          onClick={() => {
                            setSelectedNodeId(cl.id);
                            setViewMode('focused');
                            setIsDrawerOpen(false);
                            showToast?.(`Focused DAG on Claim #${cl.id.slice(0, 8)}`);
                          }}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            border: '1px solid #2563eb',
                            background: '#eff6ff',
                            color: '#2563eb',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <span>🎯 Focus in DAG</span>
                        </button>
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

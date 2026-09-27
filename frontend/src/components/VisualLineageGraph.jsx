import React, { useState, useEffect, useMemo, useRef } from 'react';

export default function VisualLineageGraph({ activeOrg, activeWorkspace, showToast }) {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [blastRadius, setBlastRadius] = useState(null);
  const [loadingBlastRadius, setLoadingBlastRadius] = useState(false);

  // Departmental Workspace Scoping
  const [lineageScopeAll, setLineageScopeAll] = useState(false);
  const WORKSPACE_KEYWORDS = {
    finance: ['refund', 'billing', 'invoice', 'arr', 'payment', 'confluence', 'salesforce', 'accounting', 'pricing', 'tier', 'annual', 'dispute'],
    secops: ['security', 'firewall', 'ingress', 'iam', 'mtls', 'session', 'token', 'freeze', 'portal', 'github', 'kafka', 'baseline', 'policy'],
    hr: ['remote', 'work', 'leave', 'vacation', 'employee', 'handbook', 'people', 'guideline', 'wifi', 'stipend', 'contractor'],
    support: ['support', 'dispute', 'sla', 'ticket', 'escalation', 'jira', 'arbitration', 'customer'],
    staging: ['staging', 'sandbox', 'test', 'mock', 'simulation']
  };

  // View Mode: 'conflicts' (default clean DAG), 'focused' (centered around active asset), 'all' (sample overview)
  const [viewMode, setViewMode] = useState('conflicts');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerSearch, setDrawerSearch] = useState('');
  const [drawerDocFilter, setDrawerDocFilter] = useState('all');

  // Enterprise Filter States
  const [selectedConflictId, setSelectedConflictId] = useState('all');
  const [selectedDocFilter, setSelectedDocFilter] = useState('all');
  const [filterSeverity, setFilterSeverity] = useState('all'); // 'all', 'HIGH', 'CRITICAL', 'MEDIUM', 'LOW'
  const [filterStatus, setFilterStatus] = useState('all'); // 'all', 'review', 'resolved'
  const [filterClaimTrust, setFilterClaimTrust] = useState('all'); // 'all', 'verified', 'review', 'outdated'
  const [showOnlyConflicted, setShowOnlyConflicted] = useState(false);
  const [displayLimit, setDisplayLimit] = useState(12); // 6, 12, 24, 1000 ('all')
  const [visibleTiers, setVisibleTiers] = useState(new Set(['source', 'document', 'claim', 'conflict', 'decision']));
  const [isFilterPanelOpen, setIsFilterPanelOpen] = useState(true);

  // Free-form Canvas Pan & Zoom State
  const [zoom, setZoom] = useState(0.78);
  const [pan, setPan] = useState({ x: 30, y: 30 });
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

  // Build Comprehensive Conflict Mapping
  const conflictMap = useMemo(() => {
    const map = {};
    if (!graphData?.nodes) return map;
    const conflicts = graphData.nodes.filter(n => n.type === 'conflict');
    conflicts.forEach(c => {
      let claimA = c.data?.first_claim_id ? `cl_${c.data.first_claim_id}` : null;
      let claimB = c.data?.second_claim_id ? `cl_${c.data.second_claim_id}` : null;
      if (!claimA || !claimB) {
        const inEdges = graphData.edges?.filter(e => e.target === c.id && e.source.startsWith('cl_')) || [];
        if (!claimA && inEdges[0]) claimA = inEdges[0].source;
        if (!claimB && inEdges[1]) claimB = inEdges[1].source;
      }
      map[c.id] = {
        conflict: c,
        claimAId: claimA,
        claimBId: claimB,
        severity: c.severity || 'MEDIUM',
        status: c.status || 'HUMAN_REVIEW_REQUIRED',
        label: c.label || `Conflict: ${c.id.slice(0, 8)}`,
      };
    });
    return map;
  }, [graphData]);

  // Set of all claims involved in any conflict
  const allConflictedClaimIds = useMemo(() => {
    const set = new Set();
    Object.values(conflictMap).forEach(item => {
      if (item.claimAId) set.add(item.claimAId);
      if (item.claimBId) set.add(item.claimBId);
    });
    graphData?.nodes?.forEach(n => {
      if (n.type === 'claim' && n.status === 'conflicted') set.add(n.id);
    });
    return set;
  }, [conflictMap, graphData]);

  // Compute Connected Sets from real edges
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

    // 2nd tier connections
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

  // 1. Reactive Filtering Engine: Evaluates User Filters across the Entire Graph
  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    const nodes = graphData.nodes;
    const edges = graphData.edges || [];

    // A. If a specific conflict is selected in "Inspect Conflict" dropdown:
    if (selectedConflictId !== 'all') {
      const cItem = conflictMap[selectedConflictId];
      if (cItem) {
        const allowedIds = new Set([selectedConflictId]);
        if (cItem.claimAId) allowedIds.add(cItem.claimAId);
        if (cItem.claimBId) allowedIds.add(cItem.claimBId);

        // Add parent documents of these claims
        edges.forEach(e => {
          if ((e.target === cItem.claimAId || e.target === cItem.claimBId) && e.source.startsWith('doc_')) {
            allowedIds.add(e.source);
          }
        });
        // Add sources of these documents
        edges.forEach(e => {
          if (allowedIds.has(e.target) && e.source.startsWith('src_')) {
            allowedIds.add(e.source);
          }
        });
        // Add downstream decisions of these claims or conflict
        edges.forEach(e => {
          if ((e.source === cItem.claimAId || e.source === cItem.claimBId || e.source === selectedConflictId) && e.target.startsWith('dec_')) {
            allowedIds.add(e.target);
          }
        });

        return nodes.filter(n => allowedIds.has(n.id) && visibleTiers.has(n.type));
      }
    }

    // B. General Multi-Factor Filtering
    let result = nodes;

    // 1. Tier visibility toggle filter
    result = result.filter(n => visibleTiers.has(n.type));

    // 2. Filter by document scope
    if (selectedDocFilter !== 'all') {
      const docClaims = new Set();
      edges.forEach(e => {
        if (e.source === selectedDocFilter && e.target.startsWith('cl_')) {
          docClaims.add(e.target);
        }
      });
      const docSources = new Set();
      edges.forEach(e => {
        if (e.target === selectedDocFilter && e.source.startsWith('src_')) {
          docSources.add(e.source);
        }
      });
      const docConflicts = new Set();
      edges.forEach(e => {
        if (docClaims.has(e.source) && e.target.startsWith('cfl_')) {
          docConflicts.add(e.target);
        }
      });

      result = result.filter(n => {
        if (n.type === 'document') return n.id === selectedDocFilter;
        if (n.type === 'source') return docSources.has(n.id);
        if (n.type === 'claim') return docClaims.has(n.id);
        if (n.type === 'conflict') return docConflicts.has(n.id);
        if (n.type === 'decision') return true;
        return true;
      });
    }

    // 3. Show only conflicted paths
    if (showOnlyConflicted) {
      const activeConflicts = result.filter(n => n.type === 'conflict');
      const conflictClaimIds = new Set();
      activeConflicts.forEach(c => {
        edges.forEach(e => {
          if (e.target === c.id && e.source.startsWith('cl_')) conflictClaimIds.add(e.source);
        });
        const cItem = conflictMap[c.id];
        if (cItem?.claimAId) conflictClaimIds.add(cItem.claimAId);
        if (cItem?.claimBId) conflictClaimIds.add(cItem.claimBId);
      });

      const conflictDocIds = new Set();
      edges.forEach(e => {
        if (conflictClaimIds.has(e.target) && e.source.startsWith('doc_')) {
          conflictDocIds.add(e.source);
        }
      });

      const conflictSourceIds = new Set();
      edges.forEach(e => {
        if (conflictDocIds.has(e.target) && e.source.startsWith('src_')) {
          conflictSourceIds.add(e.source);
        }
      });

      result = result.filter(n => {
        if (n.type === 'conflict') return true;
        if (n.type === 'claim') return conflictClaimIds.has(n.id);
        if (n.type === 'document') return conflictDocIds.has(n.id);
        if (n.type === 'source') return conflictSourceIds.has(n.id);
        if (n.type === 'decision') return false;
        return false;
      });
    }

    // 4. Filter conflicts by severity
    if (filterSeverity !== 'all') {
      result = result.filter(n => {
        if (n.type !== 'conflict') return true;
        return (n.severity || '').toUpperCase() === filterSeverity.toUpperCase();
      });
    }

    // 5. Filter conflicts by resolution status
    if (filterStatus !== 'all') {
      result = result.filter(n => {
        if (n.type !== 'conflict') return true;
        return (n.status || '').toLowerCase().includes(filterStatus.toLowerCase());
      });
    }

    // 6. Filter claims by trust level
    if (filterClaimTrust !== 'all') {
      result = result.filter(n => {
        if (n.type !== 'claim') return true;
        const score = n.trustScore !== undefined ? n.trustScore : 0.85;
        if (filterClaimTrust === 'verified') return score >= 0.90;
        if (filterClaimTrust === 'review') return score < 0.90 && n.status !== 'outdated';
        if (filterClaimTrust === 'outdated') return n.status === 'outdated' || score < 0.50;
        return true;
      });
    }

    // 7. Search query across all fields
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(n => {
        return (
          n.label?.toLowerCase().includes(q) ||
          n.fullText?.toLowerCase().includes(q) ||
          n.type?.toLowerCase().includes(q) ||
          n.subType?.toLowerCase().includes(q) ||
          n.id?.toLowerCase().includes(q)
        );
      });
    }

    // 8. Departmental Workspace Scoping
    if (activeWorkspace && activeWorkspace.id !== 'all' && !lineageScopeAll) {
      const kw = WORKSPACE_KEYWORDS[activeWorkspace.id] || [];
      if (kw.length > 0) {
        const matchedIds = new Set();
        result.forEach(n => {
          const text = `${n.label || ''} ${n.fullText || ''} ${n.id || ''} ${n.subType || ''}`.toLowerCase();
          if (kw.some(k => text.includes(k))) {
            matchedIds.add(n.id);
          }
        });

        // Expand to connected neighbors so DAG structure remains intact
        edges.forEach(e => {
          if (matchedIds.has(e.source)) matchedIds.add(e.target);
          if (matchedIds.has(e.target)) matchedIds.add(e.source);
        });

        if (matchedIds.size > 0) {
          result = result.filter(n => matchedIds.has(n.id));
        }
      }
    }

    return result;
  }, [
    graphData,
    selectedConflictId,
    selectedDocFilter,
    filterSeverity,
    filterStatus,
    filterClaimTrust,
    showOnlyConflicted,
    visibleTiers,
    searchQuery,
    conflictMap,
    activeWorkspace,
    lineageScopeAll
  ]);

  // 2. Smart DAG Layout: Adaptive Density & Immediate Visibility
  const defaultPositions = useMemo(() => {
    const map = {};
    if (!filteredNodes.length) return map;

    const sources = filteredNodes.filter(n => n.type === 'source');
    const documents = filteredNodes.filter(n => n.type === 'document');
    const claims = filteredNodes.filter(n => n.type === 'claim');
    const conflicts = filteredNodes.filter(n => n.type === 'conflict');
    const decisions = filteredNodes.filter(n => n.type === 'decision');

    const limit = displayLimit === 'all' ? 1000 : Number(displayLimit);

    const activeSources = sources.slice(0, limit);
    const activeDocs = documents.slice(0, limit);

    // Prioritize conflicted claims if in conflict mode or conflict focused
    let activeClaims = claims;
    if (viewMode === 'conflicts' || showOnlyConflicted || selectedConflictId !== 'all') {
      const conflictRelatedClaimIds = new Set();
      conflicts.forEach(c => {
        const cItem = conflictMap[c.id];
        if (cItem?.claimAId) conflictRelatedClaimIds.add(cItem.claimAId);
        if (cItem?.claimBId) conflictRelatedClaimIds.add(cItem.claimBId);
      });
      activeClaims = [
        ...claims.filter(cl => conflictRelatedClaimIds.has(cl.id)),
        ...claims.filter(cl => !conflictRelatedClaimIds.has(cl.id))
      ].slice(0, limit);
    } else if (viewMode === 'focused' && selectedNodeId) {
      activeClaims = [
        ...claims.filter(n => connectedNodeMap.all.has(n.id)),
        ...claims.filter(n => !connectedNodeMap.all.has(n.id))
      ].slice(0, limit);
    } else {
      activeClaims = claims.slice(0, limit);
    }

    const activeConflicts = conflicts.slice(0, limit);
    const activeDecisions = decisions.slice(0, limit);

    // Always guarantee selected node is included if present in filteredNodes
    if (selectedNode && filteredNodes.some(n => n.id === selectedNode.id)) {
      if (selectedNode.type === 'source' && !activeSources.some(n => n.id === selectedNode.id)) activeSources.unshift(selectedNode);
      if (selectedNode.type === 'document' && !activeDocs.some(n => n.id === selectedNode.id)) activeDocs.unshift(selectedNode);
      if (selectedNode.type === 'claim' && !activeClaims.some(n => n.id === selectedNode.id)) activeClaims.unshift(selectedNode);
      if (selectedNode.type === 'conflict' && !activeConflicts.some(n => n.id === selectedNode.id)) activeConflicts.unshift(selectedNode);
      if (selectedNode.type === 'decision' && !activeDecisions.some(n => n.id === selectedNode.id)) activeDecisions.unshift(selectedNode);
    }

    // Compact X positions so all 5 columns fit comfortably in viewport
    const levels = [
      { nodes: activeSources, x: 40, type: 'source' },
      { nodes: activeDocs, x: 350, type: 'document' },
      { nodes: activeClaims, x: 660, type: 'claim' },
      { nodes: activeConflicts, x: 970, type: 'conflict' },
      { nodes: activeDecisions, x: 1280, type: 'decision' }
    ];

    levels.forEach(lvl => {
      const count = lvl.nodes.length;
      const cardSpacing = count > 10 ? 104 : count > 5 ? 116 : 124;
      // Start near top so nodes are immediately visible without scrolling
      const startY = 30;

      lvl.nodes.forEach((node, idx) => {
        map[node.id] = {
          x: lvl.x,
          y: startY + idx * cardSpacing
        };
      });
    });

    return map;
  }, [
    filteredNodes,
    displayLimit,
    viewMode,
    showOnlyConflicted,
    selectedConflictId,
    selectedNode,
    connectedNodeMap,
    conflictMap
  ]);

  // Merged positions (custom user drags take precedence)
  const nodePositions = useMemo(() => {
    return { ...defaultPositions, ...customPositions };
  }, [defaultPositions, customPositions]);

  // Filter rendered nodes based on calculated positions
  const renderedNodes = useMemo(() => {
    if (!filteredNodes) return [];
    return filteredNodes.filter(n => !!nodePositions[n.id]);
  }, [filteredNodes, nodePositions]);

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
        const isConflictConnection = e.type === 'conflict' || (selectedConflictId !== 'all' && (e.target === selectedConflictId || e.source === selectedConflictId));

        return {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          pathData,
          midX,
          midY,
          isActive,
          isConflictConnection
        };
      });
  }, [graphData, nodePositions, connectedNodeMap, selectedConflictId]);

  // Canvas Pan Handlers
  const handleCanvasMouseDown = (e) => {
    if (e.target.closest('.atlan-node-card') || e.target.closest('.canvas-btn') || e.target.closest('select') || e.target.closest('input') || e.target.closest('button')) return;
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

  // Auto-Fit Camera to visible nodes bounding box
  const handleFitView = () => {
    const visiblePositions = Object.values(nodePositions);
    if (visiblePositions.length === 0) {
      setZoom(0.78);
      setPan({ x: 30, y: 30 });
      return;
    }
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    visiblePositions.forEach(p => {
      if (p.x < minX) minX = p.x;
      if (p.x + CARD_WIDTH > maxX) maxX = p.x + CARD_WIDTH;
      if (p.y < minY) minY = p.y;
      if (p.y + CARD_HEIGHT > maxY) maxY = p.y + CARD_HEIGHT;
    });

    const graphW = maxX - minX + 60;
    const graphH = maxY - minY + 60;
    const containerW = containerRef.current ? containerRef.current.clientWidth : 1150;
    const containerH = containerRef.current ? containerRef.current.clientHeight : 600;

    const newZoom = Math.min(0.95, Math.max(0.5, Math.min(containerW / graphW, containerH / graphH)));
    const newPanX = Math.max(25, (containerW - (maxX - minX) * newZoom) / 2 - minX * newZoom);
    // Keep cards positioned comfortably near top of visible canvas area
    const newPanY = Math.max(25, 45 - minY * newZoom);

    setZoom(Number(newZoom.toFixed(2)));
    setPan({ x: Math.round(newPanX), y: Math.round(newPanY) });
    setCustomPositions({});
  };

  // Toggle visible tiers
  const toggleTier = (tier) => {
    setVisibleTiers(prev => {
      const next = new Set(prev);
      if (next.has(tier)) {
        if (next.size === 1) return prev;
        next.delete(tier);
      } else {
        next.add(tier);
      }
      return next;
    });
  };

  // Reset all filters
  const resetAllFilters = () => {
    setSelectedConflictId('all');
    setSelectedDocFilter('all');
    setFilterSeverity('all');
    setFilterStatus('all');
    setFilterClaimTrust('all');
    setShowOnlyConflicted(false);
    setDisplayLimit(12);
    setSearchQuery('');
    setVisibleTiers(new Set(['source', 'document', 'claim', 'conflict', 'decision']));
    setViewMode('conflicts');
    setPan({ x: 30, y: 30 });
    setZoom(0.78);
    showToast?.("All filters reset to standard view");
  };

  const isAnyFilterActive = useMemo(() => {
    return (
      selectedConflictId !== 'all' ||
      selectedDocFilter !== 'all' ||
      filterSeverity !== 'all' ||
      filterStatus !== 'all' ||
      filterClaimTrust !== 'all' ||
      showOnlyConflicted ||
      displayLimit !== 12 ||
      searchQuery.trim() !== '' ||
      visibleTiers.size < 5
    );
  }, [
    selectedConflictId,
    selectedDocFilter,
    filterSeverity,
    filterStatus,
    filterClaimTrust,
    showOnlyConflicted,
    displayLimit,
    searchQuery,
    visibleTiers
  ]);

  const conflictsList = useMemo(() => {
    return graphData?.nodes?.filter(n => n.type === 'conflict') || [];
  }, [graphData]);

  const documentsList = useMemo(() => {
    return graphData?.nodes?.filter(n => n.type === 'document') || [];
  }, [graphData]);

  // Auto-recenter when selecting a specific conflict
  useEffect(() => {
    if (selectedConflictId !== 'all') {
      const timer = setTimeout(() => {
        handleFitView();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [selectedConflictId]);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      
      {/* 1. Top Atlan-Style Asset Bar with Presets & Navigation */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: '10px',
        padding: '8px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        {/* Left: Focus Asset Dropdown Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600 }}>All assets</span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>&rsaquo;</span>
          
          <select
            value={selectedNodeId || ''}
            onChange={(e) => {
              setSelectedNodeId(e.target.value);
              if (viewMode === 'conflicts') setViewMode('focused');
            }}
            style={{
              padding: '5px 8px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              background: '#f8fafc',
              fontSize: '0.78rem',
              fontWeight: 700,
              color: '#2026d2',
              cursor: 'pointer',
              maxWidth: '280px',
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

          {/* Departmental Workspace Scope Badge & All Combined Toggle */}
          {activeWorkspace && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 9px',
                borderRadius: '6px',
                background: activeWorkspace.id !== 'all' && !lineageScopeAll ? 'rgba(37,99,235,0.08)' : '#f1f5f9',
                border: `1px solid ${activeWorkspace.id !== 'all' && !lineageScopeAll ? 'rgba(37,99,235,0.25)' : '#cbd5e1'}`,
                fontSize: '0.74rem',
                fontWeight: 700,
                color: activeWorkspace.id !== 'all' && !lineageScopeAll ? '#1d4ed8' : '#475569'
              }}>
                <span>{activeWorkspace.icon || '🏢'}</span>
                <span>{lineageScopeAll ? 'All Workspaces (Unified)' : activeWorkspace.name}</span>
                {activeWorkspace.id !== 'all' && !lineageScopeAll && (
                  <span style={{ fontSize: '0.66rem', color: '#16a34a', background: 'rgba(22,163,74,0.1)', padding: '1px 5px', borderRadius: '4px' }}>
                    Isolated
                  </span>
                )}
              </span>

              {activeWorkspace.id !== 'all' && (
                <button
                  type="button"
                  onClick={() => setLineageScopeAll(prev => !prev)}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '5px',
                    border: '1px solid #cbd5e1',
                    background: lineageScopeAll ? '#2563eb' : '#ffffff',
                    color: lineageScopeAll ? '#ffffff' : '#334155',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  title={lineageScopeAll ? "Return to scoped departmental pipeline" : "Show all combined enterprise resources across all departments"}
                >
                  {lineageScopeAll ? "↩ Back to Scoped" : "🌐 View All Combined"}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Center: DAG Perspective Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '3px', background: '#f1f5f9', padding: '2px', borderRadius: '7px', border: '1px solid #e2e8f0' }}>
          <button
            onClick={() => {
              setViewMode('conflicts');
              const firstConf = conflictsList[0];
              if (firstConf) setSelectedNodeId(firstConf.id);
            }}
            style={{
              padding: '4px 10px',
              fontSize: '0.72rem',
              fontWeight: 700,
              borderRadius: '5px',
              border: 'none',
              cursor: 'pointer',
              background: viewMode === 'conflicts' ? '#ea580c' : 'transparent',
              color: viewMode === 'conflicts' ? '#fff' : '#475569',
              boxShadow: viewMode === 'conflicts' ? '0 1px 4px rgba(234,88,12,0.3)' : 'none',
              transition: 'all 0.15s ease'
            }}
            title="Focus exclusively on contradictory claims and their lineage"
          >
            ⚡ Contradictions DAG ({conflictsList.length})
          </button>
          <button
            onClick={() => setViewMode('focused')}
            style={{
              padding: '4px 10px',
              fontSize: '0.72rem',
              fontWeight: 700,
              borderRadius: '5px',
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
              padding: '4px 10px',
              fontSize: '0.72rem',
              fontWeight: 700,
              borderRadius: '5px',
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={() => setIsFilterPanelOpen(prev => !prev)}
            style={{
              padding: '5px 10px',
              fontSize: '0.74rem',
              fontWeight: 700,
              borderRadius: '6px',
              border: isAnyFilterActive ? '1.5px solid #ea580c' : '1px solid #cbd5e1',
              background: isAnyFilterActive ? '#fff7ed' : '#f8fafc',
              color: isAnyFilterActive ? '#ea580c' : '#334155',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Toggle Filter Control Panel"
          >
            <span>⚙️ Filters</span>
            {isAnyFilterActive && (
              <span style={{
                background: '#ea580c',
                color: '#fff',
                borderRadius: '8px',
                padding: '1px 5px',
                fontSize: '0.62rem'
              }}>
                Active
              </span>
            )}
          </button>

          <button
            onClick={() => setIsDrawerOpen(true)}
            className="btn btn-secondary canvas-btn"
            style={{ padding: '5px 10px', fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '4px', background: '#f8fafc', border: '1px solid #cbd5e1' }}
            title="Browse all extracted atomic claims in searchable list"
          >
            <span>📋</span>
            <span>Claims Drawer ({graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0})</span>
          </button>
          
          <button
            onClick={fetchLineage}
            disabled={loading}
            className="btn btn-secondary canvas-btn"
            style={{ padding: '5px 10px', fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <span>🔄</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* 2. Compact Enterprise Filtering Console */}
      {isFilterPanelOpen && (
        <div style={{
          background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
          border: '1px solid #cbd5e1',
          borderRadius: '10px',
          padding: '10px 14px',
          boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          {/* Row 1: Primary Selectors in a Tight Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
            gap: '8px',
            alignItems: 'center'
          }}>
            {/* A. Conflict Isolation Selector */}
            <div>
              <label style={{ display: 'block', fontSize: '0.66rem', fontWeight: 700, color: '#ea580c', marginBottom: '2px', textTransform: 'uppercase' }}>
                ⚡ Focus Conflict
              </label>
              <select
                value={selectedConflictId}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedConflictId(val);
                  if (val !== 'all') {
                    setSelectedNodeId(val);
                    setViewMode('conflicts');
                    showToast?.(`Spotlighted Conflict in DAG`);
                  }
                }}
                style={{
                  width: '100%',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  border: selectedConflictId !== 'all' ? '1.5px solid #ea580c' : '1px solid #cbd5e1',
                  background: selectedConflictId !== 'all' ? '#fff7ed' : '#ffffff',
                  fontSize: '0.75rem',
                  fontWeight: selectedConflictId !== 'all' ? 700 : 500,
                  color: selectedConflictId !== 'all' ? '#ea580c' : '#334155',
                  outline: 'none',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Conflicts ({conflictsList.length})</option>
                {conflictsList.map((c, i) => (
                  <option key={c.id} value={c.id}>
                    #{i + 1} [{c.severity || 'HIGH'}] {c.label}
                  </option>
                ))}
              </select>
            </div>

            {/* B. Document / Policy Selector */}
            <div>
              <label style={{ display: 'block', fontSize: '0.66rem', fontWeight: 700, color: '#0284c7', marginBottom: '2px', textTransform: 'uppercase' }}>
                📄 Filter by Document
              </label>
              <select
                value={selectedDocFilter}
                onChange={(e) => {
                  setSelectedDocFilter(e.target.value);
                  if (e.target.value !== 'all') {
                    setSelectedNodeId(e.target.value);
                  }
                }}
                style={{
                  width: '100%',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  border: selectedDocFilter !== 'all' ? '1.5px solid #0284c7' : '1px solid #cbd5e1',
                  background: selectedDocFilter !== 'all' ? '#f0f9ff' : '#ffffff',
                  fontSize: '0.75rem',
                  fontWeight: selectedDocFilter !== 'all' ? 700 : 500,
                  color: selectedDocFilter !== 'all' ? '#0284c7' : '#334155',
                  outline: 'none',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Policies ({documentsList.length})</option>
                {documentsList.map(d => (
                  <option key={d.id} value={d.id}>
                    {d.label}
                  </option>
                ))}
              </select>
            </div>

            {/* C. Conflict Severity Filter */}
            <div>
              <label style={{ display: 'block', fontSize: '0.66rem', fontWeight: 700, color: '#64748b', marginBottom: '2px', textTransform: 'uppercase' }}>
                ⚖️ Severity
              </label>
              <select
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
                style={{
                  width: '100%',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  border: filterSeverity !== 'all' ? '1.5px solid #2563eb' : '1px solid #cbd5e1',
                  background: filterSeverity !== 'all' ? '#eff6ff' : '#ffffff',
                  fontSize: '0.75rem',
                  color: '#334155',
                  outline: 'none',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Severities</option>
                <option value="HIGH">High Severity Only</option>
                <option value="CRITICAL">Critical Severity Only</option>
                <option value="MEDIUM">Medium Severity</option>
                <option value="LOW">Low Severity</option>
              </select>
            </div>

            {/* D. Conflict Status Filter */}
            <div>
              <label style={{ display: 'block', fontSize: '0.66rem', fontWeight: 700, color: '#64748b', marginBottom: '2px', textTransform: 'uppercase' }}>
                🏷️ Status
              </label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                style={{
                  width: '100%',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  border: filterStatus !== 'all' ? '1.5px solid #2563eb' : '1px solid #cbd5e1',
                  background: filterStatus !== 'all' ? '#eff6ff' : '#ffffff',
                  fontSize: '0.75rem',
                  color: '#334155',
                  outline: 'none',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Statuses</option>
                <option value="review">Review Required</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>

            {/* E. Claim Trust Filter */}
            <div>
              <label style={{ display: 'block', fontSize: '0.66rem', fontWeight: 700, color: '#64748b', marginBottom: '2px', textTransform: 'uppercase' }}>
                🛡️ Claim Trust
              </label>
              <select
                value={filterClaimTrust}
                onChange={(e) => setFilterClaimTrust(e.target.value)}
                style={{
                  width: '100%',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  border: filterClaimTrust !== 'all' ? '1.5px solid #16a34a' : '1px solid #cbd5e1',
                  background: filterClaimTrust !== 'all' ? '#f0fdf4' : '#ffffff',
                  fontSize: '0.75rem',
                  color: '#334155',
                  outline: 'none',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Trust Levels</option>
                <option value="verified">Verified (≥ 90%)</option>
                <option value="review">Review Needed (&lt; 90%)</option>
                <option value="outdated">Outdated / Superseded</option>
              </select>
            </div>

            {/* F. Display Density */}
            <div>
              <label style={{ display: 'block', fontSize: '0.66rem', fontWeight: 700, color: '#64748b', marginBottom: '2px', textTransform: 'uppercase' }}>
                📊 Column Density
              </label>
              <select
                value={displayLimit}
                onChange={(e) => setDisplayLimit(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                style={{
                  width: '100%',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#ffffff',
                  fontSize: '0.75rem',
                  color: '#334155',
                  outline: 'none',
                  cursor: 'pointer'
                }}
              >
                <option value={6}>Compact (6 per column)</option>
                <option value={12}>Standard (12 per column)</option>
                <option value={24}>Expanded (24 per column)</option>
                <option value="all">All Matched (Unlimited)</option>
              </select>
            </div>
          </div>

          {/* Row 2: Quick Toggles & Tier Visibility Pills */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px',
            borderTop: '1px solid #e2e8f0',
            paddingTop: '6px'
          }}>
            {/* Left: Conflicted-Only Mode & Visible Tiers */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <button
                onClick={() => {
                  setShowOnlyConflicted(prev => !prev);
                  if (!showOnlyConflicted) {
                    showToast?.("Focused strictly on contradictory policy paths");
                  }
                }}
                style={{
                  padding: '3px 10px',
                  borderRadius: '16px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  border: showOnlyConflicted ? '1.5px solid #ea580c' : '1px solid #cbd5e1',
                  background: showOnlyConflicted ? '#ea580c' : '#ffffff',
                  color: showOnlyConflicted ? '#ffffff' : '#475569',
                  boxShadow: showOnlyConflicted ? '0 1px 4px rgba(234,88,12,0.3)' : 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.15s ease'
                }}
              >
                <span>⚠️ Conflicted Only</span>
                {showOnlyConflicted && <span>✓</span>}
              </button>

              <span style={{ fontSize: '0.68rem', color: '#94a3b8', margin: '0 2px' }}>| Tiers:</span>

              {/* Tier Toggle Pills */}
              {[
                { type: 'source', label: 'Sources', icon: '🔌', count: graphData?.nodes?.filter(n => n.type === 'source')?.length || 0, color: '#2026d2' },
                { type: 'document', label: 'Docs', icon: '📄', count: documentsList.length, color: '#0284c7' },
                { type: 'claim', label: 'Claims', icon: '⚡', count: graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0, color: '#16a34a' },
                { type: 'conflict', label: 'Conflicts', icon: '⚖️', count: conflictsList.length, color: '#ea580c' },
                { type: 'decision', label: 'Decisions', icon: '🤖', count: graphData?.nodes?.filter(n => n.type === 'decision')?.length || 0, color: '#7c3aed' },
              ].map(t => {
                const isVisible = visibleTiers.has(t.type);
                return (
                  <button
                    key={t.type}
                    onClick={() => toggleTier(t.type)}
                    style={{
                      padding: '3px 7px',
                      borderRadius: '5px',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      border: isVisible ? `1px solid ${t.color}` : '1px solid #e2e8f0',
                      background: isVisible ? `${t.color}12` : '#f1f5f9',
                      color: isVisible ? t.color : '#94a3b8',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '3px',
                      opacity: isVisible ? 1 : 0.6,
                      transition: 'all 0.15s ease'
                    }}
                    title={`Toggle visibility of ${t.label} tier`}
                  >
                    <span>{t.icon}</span>
                    <span>{t.label}</span>
                    <span style={{ fontSize: '0.62rem', fontWeight: 800, background: isVisible ? `${t.color}25` : '#cbd5e1', padding: '1px 3px', borderRadius: '3px' }}>
                      {t.count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Right: Active Count Summary & Clear Filters */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                Showing <strong>{renderedNodes.length}</strong> of <strong>{graphData?.nodes?.length || 0}</strong> nodes
              </span>

              {isAnyFilterActive && (
                <button
                  onClick={resetAllFilters}
                  style={{
                    padding: '3px 8px',
                    borderRadius: '5px',
                    border: '1px solid #cbd5e1',
                    background: '#ffffff',
                    color: '#ef4444',
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '3px'
                  }}
                  title="Reset all filters to standard view"
                >
                  <span>✕ Clear Filters</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 3. Interactive DAG Canvas */}
      <div style={{ position: 'relative', width: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)', background: '#fff' }}>
        
        {/* Floating Toolbar (Top-Right) */}
        <div style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          zIndex: 30,
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(8px)',
          padding: '5px 8px',
          borderRadius: '8px',
          boxShadow: '0 4px 14px rgba(0,0,0,0.08)',
          border: '1px solid #e2e8f0'
        }}>
          {/* Find in canvas (Global across all nodes) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', paddingRight: '6px', borderRight: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b' }}>🔍</span>
            <input
              type="text"
              placeholder="Find in canvas..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                border: 'none',
                background: 'transparent',
                fontSize: '0.76rem',
                outline: 'none',
                width: '120px',
                color: 'var(--text-main)'
              }}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: '#94a3b8', fontSize: '0.72rem' }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Zoom Controls */}
          <button
            onClick={() => setZoom(z => Math.max(0.4, Number((z - 0.1).toFixed(2))))}
            className="canvas-btn"
            style={{ width: '24px', height: '24px', borderRadius: '5px', border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontWeight: 700, fontSize: '0.8rem' }}
            title="Zoom Out"
          >
            -
          </button>
          <span style={{ fontSize: '0.7rem', fontWeight: 600, minWidth: '30px', textAlign: 'center', color: '#475569' }}>
            {(zoom * 100).toFixed(0)}%
          </span>
          <button
            onClick={() => setZoom(z => Math.min(1.4, Number((z + 0.1).toFixed(2))))}
            className="canvas-btn"
            style={{ width: '24px', height: '24px', borderRadius: '5px', border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontWeight: 700, fontSize: '0.8rem' }}
            title="Zoom In"
          >
            +
          </button>
          <button
            onClick={handleFitView}
            className="canvas-btn"
            style={{ padding: '0 8px', height: '24px', borderRadius: '5px', border: '1px solid #2563eb', background: '#eff6ff', cursor: 'pointer', fontSize: '0.7rem', color: '#2563eb', fontWeight: 700 }}
            title="Auto-Fit all visible nodes to screen"
          >
            ⛶ Fit View
          </button>
        </div>

        {/* Floating Legend / Quick Status at bottom left */}
        <div style={{
          position: 'absolute',
          bottom: '12px',
          left: '12px',
          zIndex: 30,
          background: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(8px)',
          padding: '6px 12px',
          borderRadius: '7px',
          boxShadow: '0 3px 10px rgba(0,0,0,0.06)',
          border: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '0.68rem',
          color: '#475569'
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#2026d2' }} /> Data Source
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#0284c7' }} /> Document
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#16a34a' }} /> Atomic Claim
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#ea580c' }} /> Contradiction
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#7c3aed' }} /> AI Decision
          </span>
          <span style={{ color: '#94a3b8', marginLeft: '2px' }}>| Drag nodes freely to customize layout</span>
        </div>

        {/* Free-form Pan Canvas Container */}
        <div
          ref={containerRef}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{
            height: '640px',
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
                width: '3600px',
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
                const isConflictLine = edge.type === 'conflict' || edge.isConflictConnection;
                const strokeColor = isConflictLine
                  ? '#ea580c'
                  : edge.isActive
                    ? edge.type === 'decision_grounding' ? '#7c3aed' : '#2563eb'
                    : '#cbd5e1';

                const strokeWidth = isConflictLine ? 2.5 : edge.isActive ? 2.2 : 1.5;
                const marker = isConflictLine
                  ? 'url(#atlan-arrow-conflict)'
                  : edge.isActive
                    ? edge.type === 'decision_grounding' ? 'url(#atlan-arrow-decision)' : 'url(#atlan-arrow-active)'
                    : 'url(#atlan-arrow-default)';

                return (
                  <g key={edge.id}>
                    <path
                      d={edge.pathData}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeDasharray={isConflictLine || edge.isActive ? '6 3' : 'none'}
                      markerEnd={marker}
                      style={{
                        transition: 'stroke 0.2s ease, stroke-width 0.2s ease',
                        animation: isConflictLine || edge.isActive ? 'dash-flow 1.5s linear infinite' : 'none'
                      }}
                    />

                    {/* Connector badge on bezier curve */}
                    <circle
                      cx={edge.midX}
                      cy={edge.midY}
                      r="9"
                      fill="#fff"
                      stroke={strokeColor}
                      strokeWidth={isConflictLine ? 2 : 1.5}
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

            {/* Empty State Banner */}
            {renderedNodes.length === 0 && (
              <div style={{
                position: 'absolute',
                top: '200px',
                left: '260px',
                textAlign: 'center',
                background: 'rgba(255,255,255,0.96)',
                backdropFilter: 'blur(8px)',
                padding: '32px 40px',
                borderRadius: '14px',
                border: '1px solid #cbd5e1',
                boxShadow: '0 12px 32px rgba(0,0,0,0.06)',
                maxWidth: '500px',
                pointerEvents: 'auto'
              }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🔎</div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#1e293b', margin: '0 0 8px 0' }}>
                  No Nodes Match Active Filters
                </h3>
                <p style={{ fontSize: '0.82rem', color: '#64748b', lineHeight: 1.55, margin: '0 0 14px 0' }}>
                  No lineage nodes match your current combination of filters. Try clearing some filters or resetting to default view.
                </p>
                <button
                  onClick={resetAllFilters}
                  className="btn btn-primary"
                  style={{ padding: '6px 16px', fontSize: '0.78rem' }}
                >
                  Reset Filters to Default
                </button>
              </div>
            )}

            {/* Draggable Node Cards */}
            {renderedNodes.map(node => {
              const pos = nodePositions[node.id] || { x: 100, y: 100 };
              const isSelected = selectedNodeId === node.id;
              const isConnected = connectedNodeMap.all.has(node.id);
              const isConflictedClaim = allConflictedClaimIds.has(node.id);

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

              // Special highlight for contradictory claims
              if (isConflictedClaim && node.type === 'claim') {
                borderColor = '#ea580c';
                badgeColor = '#ea580c';
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
                    border: isSelected
                      ? `2px solid ${borderColor}`
                      : isConflictedClaim
                        ? '1.5px solid #ea580c'
                        : isConnected
                          ? `1.5px solid ${borderColor}`
                          : '1px solid #cbd5e1',
                    boxShadow: isSelected
                      ? `0 0 0 4px ${borderColor}30, 0 8px 24px rgba(0,0,0,0.12)`
                      : isConflictedClaim
                        ? '0 0 0 2px rgba(234,88,12,0.25), 0 4px 14px rgba(234,88,12,0.15)'
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
                    zIndex: isSelected ? 20 : isConflictedClaim ? 15 : isConnected ? 10 : 5,
                    transition: draggedNodeId === node.id ? 'none' : 'box-shadow 0.15s ease, border-color 0.15s ease'
                  }}
                >
                  {/* Home / Focus Asset Badge */}
                  {isSelected && (
                    <div style={{
                      position: 'absolute',
                      top: '-14px',
                      left: '12px',
                      background: borderColor,
                      color: '#fff',
                      borderRadius: '5px 5px 0 0',
                      padding: '2px 8px',
                      fontSize: '0.62rem',
                      fontWeight: 700,
                      boxShadow: `0 2px 6px ${borderColor}40`,
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
                      {isConflictedClaim && node.type === 'claim' ? '⚠️ CONTRADICTION' : categoryLabel}
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

                  {/* Card Body: Entity Title */}
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

                  {/* Card Footer: Metadata / Scope */}
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

      {/* 4. Selected Entity Inspector & Conflict Resolution Console */}
      {selectedNode && (
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '16px 20px',
          display: 'grid',
          gridTemplateColumns: 'minmax(300px, 1.2fr) minmax(320px, 1fr)',
          gap: '18px',
          alignItems: 'start'
        }}>
          {/* Left Column: Node Details & Lineage Stats */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '22px' }}>
                {selectedNode.type === 'source' ? '🔌' : selectedNode.type === 'document' ? '📄' : selectedNode.type === 'claim' ? '⚡' : selectedNode.type === 'conflict' ? '⚖️' : '🤖'}
              </span>
              <div>
                <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)' }}>
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
              <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Upstream Roots</span>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0284c7', marginTop: '2px' }}>{connectedNodeMap.up.size}</div>
              </div>
              <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Downstream Targets</span>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#7c3aed', marginTop: '2px' }}>{connectedNodeMap.down.size}</div>
              </div>
              <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Trust Score</span>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#16a34a', marginTop: '2px' }}>
                  {selectedNode.trustScore !== undefined ? `${(selectedNode.trustScore * 100).toFixed(0)}%` : '98%'}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Contextual Inspector */}
          <div>
            {selectedNode.type === 'conflict' ? (
              /* Dedicated Side-by-Side Conflict Discrepancy Viewer */
              (() => {
                const cItem = conflictMap[selectedNode.id];
                const claimA = graphData?.nodes?.find(n => n.id === cItem?.claimAId);
                const claimB = graphData?.nodes?.find(n => n.id === cItem?.claimBId);

                return (
                  <div style={{
                    background: 'rgba(234,88,12,0.05)',
                    border: '1px solid rgba(234,88,12,0.3)',
                    borderRadius: '10px',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#ea580c' }}>
                        ⚖️ Contradiction Comparison
                      </span>
                      <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                        {selectedNode.severity || 'HIGH'} SEVERITY
                      </span>
                    </div>

                    {/* Claim A vs Claim B Comparison Box */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <div style={{ background: '#fff', padding: '10px', borderRadius: '8px', border: '1px solid #fed7aa', fontSize: '0.74rem' }}>
                        <div style={{ fontWeight: 800, color: '#ea580c', marginBottom: '4px' }}>Claim A (Candidate)</div>
                        <p style={{ margin: 0, color: '#334155', lineHeight: 1.35 }}>
                          "{claimA?.fullText || claimA?.label || 'Loading claim...'}"
                        </p>
                      </div>
                      <div style={{ background: '#fff', padding: '10px', borderRadius: '8px', border: '1px solid #fed7aa', fontSize: '0.74rem' }}>
                        <div style={{ fontWeight: 800, color: '#2563eb', marginBottom: '4px' }}>Claim B (Contender)</div>
                        <p style={{ margin: 0, color: '#334155', lineHeight: 1.35 }}>
                          "{claimB?.fullText || claimB?.label || 'Loading claim...'}"
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
                      <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                        Status: <strong>{selectedNode.status || 'Pending Review'}</strong>
                      </span>
                      <button
                        onClick={() => {
                          setSelectedConflictId(selectedNode.id);
                          setViewMode('conflicts');
                          showToast?.("Isolated conflict lineage on canvas");
                        }}
                        style={{
                          padding: '4px 12px',
                          borderRadius: '6px',
                          background: '#ea580c',
                          color: '#fff',
                          border: 'none',
                          fontSize: '0.74rem',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        ⚡ Isolate Conflict DAG
                      </button>
                    </div>
                  </div>
                );
              })()
            ) : selectedNode.type === 'claim' ? (
              /* Blast Radius Simulation */
              <div style={{
                background: blastRadius?.risk_tier === 'CRITICAL' || blastRadius?.risk_tier === 'HIGH' ? 'rgba(234,88,12,0.06)' : 'rgba(25,195,125,0.06)',
                border: `1px solid ${blastRadius?.risk_tier === 'CRITICAL' || blastRadius?.risk_tier === 'HIGH' ? 'rgba(234,88,12,0.3)' : 'rgba(25,195,125,0.3)'}`,
                borderRadius: '10px',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
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
                  <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.74rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Connected Conflicts: </span>
                    <strong style={{ color: '#ea580c' }}>{blastRadius?.connected_conflicts_count || 0}</strong>
                  </div>
                  <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.74rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Affected AI Decisions: </span>
                    <strong style={{ color: '#7c3aed' }}>{blastRadius?.impacted_decisions_count || 0}</strong>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ background: 'var(--bg-card)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-color)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <strong style={{ color: 'var(--text-main)' }}>Lineage Context:</strong> Select an individual <strong>Atomic Claim (⚡)</strong> or <strong>Contradiction (⚖️)</strong> to inspect connected rules and downstream AI decisions.
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. Slide-Out All Claims Explorer Drawer */}
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
          {/* Backdrop */}
          <div style={{ flex: 1 }} onClick={() => setIsDrawerOpen(false)} />

          {/* Drawer Content */}
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
            {/* Header */}
            <div style={{
              padding: '18px 22px',
              borderBottom: '1px solid #e2e8f0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#f8fafc'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '18px' }}>⚡</span>
                  <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: '#0f172a' }}>
                    Enterprise Atomic Claims Explorer
                  </h3>
                </div>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.76rem', color: '#64748b' }}>
                  Search and inspect all {graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0} atomic policy rules extracted across documents.
                </p>
              </div>
              <button
                onClick={() => setIsDrawerOpen(false)}
                style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '7px',
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#475569'
                }}
              >
                ✕
              </button>
            </div>

            {/* Filter & Search */}
            <div style={{ padding: '12px 22px', borderBottom: '1px solid #f1f5f9', background: '#fff', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '220px', position: 'relative' }}>
                <input
                  type="text"
                  placeholder="Search claim text, threshold, topic..."
                  value={drawerSearch}
                  onChange={(e) => setDrawerSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 10px 7px 30px',
                    borderRadius: '7px',
                    border: '1px solid #cbd5e1',
                    fontSize: '0.8rem',
                    outline: 'none'
                  }}
                />
                <span style={{ position: 'absolute', left: '10px', top: '8px', fontSize: '0.8rem', color: '#94a3b8' }}>🔍</span>
              </div>

              <select
                value={drawerDocFilter}
                onChange={(e) => setDrawerDocFilter(e.target.value)}
                style={{
                  padding: '7px 10px',
                  borderRadius: '7px',
                  border: '1px solid #cbd5e1',
                  fontSize: '0.78rem',
                  background: '#f8fafc',
                  maxWidth: '220px',
                  outline: 'none'
                }}
              >
                <option value="all">All Documents ({documentsList.length})</option>
                {documentsList.map(d => (
                  <option key={d.id} value={d.id}>{d.label}</option>
                ))}
              </select>
            </div>

            {/* Scrollable Claims List */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '14px 22px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
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
                  const isConflicted = allConflictedClaimIds.has(cl.id);

                  return (
                    <div
                      key={cl.id}
                      style={{
                        padding: '12px 14px',
                        borderRadius: '9px',
                        border: isConflicted ? '1.5px solid #ea580c' : '1px solid #e2e8f0',
                        background: isConflicted ? '#fff7ed' : '#ffffff',
                        boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '7px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '0.66rem', fontWeight: 800, color: '#64748b' }}>#{idx + 1}</span>
                          <span style={{ fontSize: '0.68rem', fontWeight: 700, color: '#0284c7' }}>
                            📄 {parentDoc?.label || 'Parent Document'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span className={isConflicted ? 'badge badge-warning' : 'badge badge-verified'} style={{ fontSize: '0.64rem' }}>
                            {isConflicted ? '⚠️ In Conflict' : 'Verified'}
                          </span>
                          <span className="badge badge-verified" style={{ fontSize: '0.64rem' }}>
                            {((cl.trustScore || 0.92) * 100).toFixed(0)}% Trust
                          </span>
                        </div>
                      </div>

                      <p style={{ margin: 0, fontSize: '0.8rem', color: '#1e293b', lineHeight: 1.4, fontWeight: 500 }}>
                        "{cl.fullText || cl.label}"
                      </p>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '3px', borderTop: '1px solid #f1f5f9', paddingTop: '6px' }}>
                        <span style={{ fontSize: '0.66rem', color: '#64748b' }}>
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
                            padding: '3px 8px',
                            borderRadius: '5px',
                            border: '1px solid #2563eb',
                            background: '#eff6ff',
                            color: '#2563eb',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px'
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

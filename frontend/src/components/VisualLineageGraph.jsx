import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Zap,
  Filter,
  Layers,
  FileText,
  ShieldCheck,
  Scale,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sliders,
  Eye,
  RefreshCw,
  Search,
  Database,
  Building2,
  ChevronDown,
  X,
  Bot,
  BarChart3,
  Home,
  ExternalLink,
  Share2,
  Download,
  ChevronRight,
  ChevronLeft
} from 'lucide-react';

const CARD_WIDTH = 260;
const CARD_HEIGHT = 76;

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
  const [isImpactReportOpen, setIsImpactReportOpen] = useState(false);

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

  // Enterprise Scalability & Grouping Controls
  const [groupCleanClaims, setGroupCleanClaims] = useState(true);
  const [causalSubgraphOnly, setCausalSubgraphOnly] = useState(false);
  const [lineageGranularity, setLineageGranularity] = useState('document'); // 'document' (default clean flow) or 'claim' (granular provenance)
  const [expandedDocIds, setExpandedDocIds] = useState(new Set());

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

  const conflictsList = useMemo(() => {
    return graphData?.nodes?.filter(n => n.type === 'conflict') || [];
  }, [graphData]);

  const documentsList = useMemo(() => {
    return graphData?.nodes?.filter(n => n.type === 'document') || [];
  }, [graphData]);

  const decisionsList = useMemo(() => {
    return graphData?.nodes?.filter(n => n.type === 'decision') || [];
  }, [graphData]);

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

    // Also include conflict nodes connecting any claims in 'all'
    graphData.edges.forEach(e => {
      if (all.has(e.source) && e.target.startsWith('cfl_')) {
        all.add(e.target);
        activeEdgeIds.add(e.id);
      }
      if (all.has(e.target) && e.source.startsWith('cfl_')) {
        all.add(e.source);
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

    // 9. Context-Driven Subgraph Query (k=2 depth causal trace)
    if (causalSubgraphOnly && selectedNodeId) {
      result = result.filter(n => connectedNodeMap.all.has(n.id));
    }

    // 10. Anomaly Grouping: Roll up clean/verified claims into summary cluster pills
    // Keep only active contradictions and low-trust/disputed claims expanded!
    if (groupCleanClaims) {
      const allClaims = result.filter(n => n.type === 'claim');
      const nonClaims = result.filter(n => n.type !== 'claim');
      
      const cleanClaims = [];
      const anomalousClaims = [];

      allClaims.forEach(cl => {
        const isConflicted = allConflictedClaimIds.has(cl.id) || cl.status === 'conflicted';
        const isLowTrust = cl.trustScore !== undefined && cl.trustScore < 0.85;
        if (isConflicted || isLowTrust) {
          anomalousClaims.push(cl);
        } else {
          cleanClaims.push(cl);
        }
      });

      const clusterNodes = [];
      if (cleanClaims.length > 0) {
        const cleanByDoc = {};
        cleanClaims.forEach(cl => {
          let parentDoc = 'general';
          edges.forEach(e => {
            if (e.target === cl.id && e.source.startsWith('doc_')) parentDoc = e.source;
          });
          if (!cleanByDoc[parentDoc]) cleanByDoc[parentDoc] = [];
          cleanByDoc[parentDoc].push(cl);
        });

        Object.entries(cleanByDoc).forEach(([docId, cList]) => {
          const docNode = nodes.find(n => n.id === docId);
          clusterNodes.push({
            id: `cluster_clean_${docId}`,
            type: 'claim_cluster',
            label: `${cList.length} Verified Claims`,
            subType: 'verified_cluster',
            docId,
            docTitle: docNode?.label || 'Policy Corpus',
            count: cList.length,
            claimIds: cList.map(c => c.id),
            fullText: `Cluster of ${cList.length} verified baseline claims without contradictions.`
          });
        });
      }

      result = [...nonClaims, ...anomalousClaims, ...clusterNodes];
    }

    // 11. Document-Level vs Claim-Level Granularity Filter
    if (lineageGranularity === 'document') {
      result = result.filter(n => {
        if (n.type !== 'claim' && n.type !== 'claim_cluster') return true;
        let parentDocId = n.docId;
        if (!parentDocId) {
          edges.forEach(e => {
            if (e.target === n.id && e.source.startsWith('doc_')) parentDocId = e.source;
          });
        }
        if (parentDocId && expandedDocIds.has(parentDocId)) return true;
        if (selectedNodeId === n.id) return true;
        if (selectedConflictId !== 'all') {
          const cItem = conflictMap[selectedConflictId];
          if (cItem?.claimAId === n.id || cItem?.claimBId === n.id) return true;
        }
        return false;
      });
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
    lineageScopeAll,
    causalSubgraphOnly,
    selectedNodeId,
    groupCleanClaims,
    allConflictedClaimIds,
    connectedNodeMap,
    lineageGranularity,
    expandedDocIds
  ]);

  // 2. Smart DAG Layout: Adaptive Density & Immediate Visibility
  const defaultPositions = useMemo(() => {
    const map = {};
    if (!filteredNodes.length) return map;

    const sources = filteredNodes.filter(n => n.type === 'source');
    const documents = filteredNodes.filter(n => n.type === 'document');
    const claims = filteredNodes.filter(n => n.type === 'claim' || n.type === 'claim_cluster');
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
        ...claims.filter(cl => cl.type === 'claim_cluster' || conflictRelatedClaimIds.has(cl.id)),
        ...claims.filter(cl => cl.type !== 'claim_cluster' && !conflictRelatedClaimIds.has(cl.id))
      ];
    } else if (viewMode === 'focused' && selectedNodeId) {
      activeClaims = [
        ...claims.filter(n => connectedNodeMap.all.has(n.id) || n.type === 'claim_cluster'),
        ...claims.filter(n => !connectedNodeMap.all.has(n.id) && n.type !== 'claim_cluster')
      ];
    }

    // High-Density Column Overflow Cluster Pill (when > 12 nodes in claims column)
    if (activeClaims.length > 12 && displayLimit !== 'all') {
      const topCount = 11;
      const overflowCount = activeClaims.length - topCount;
      const topClaims = activeClaims.slice(0, topCount);
      const densityCluster = {
        id: 'cluster_overflow_claims',
        type: 'density_cluster',
        label: `+${overflowCount} More Claims`,
        count: overflowCount,
        desc: 'Click to expand full column density'
      };
      activeClaims = [...topClaims, densityCluster];
    } else {
      activeClaims = activeClaims.slice(0, limit);
    }

    const activeConflicts = conflicts.slice(0, limit);
    const activeDecisions = decisions.slice(0, limit);

    // Always guarantee selected node is included if present in filteredNodes
    if (selectedNode && filteredNodes.some(n => n.id === selectedNode.id)) {
      if (selectedNode.type === 'source' && !activeSources.some(n => n.id === selectedNode.id)) activeSources.unshift(selectedNode);
      if (selectedNode.type === 'document' && !activeDocs.some(n => n.id === selectedNode.id)) activeDocs.unshift(selectedNode);
      if ((selectedNode.type === 'claim' || selectedNode.type === 'claim_cluster') && !activeClaims.some(n => n.id === selectedNode.id)) activeClaims.unshift(selectedNode);
      if (selectedNode.type === 'conflict' && !activeConflicts.some(n => n.id === selectedNode.id)) activeConflicts.unshift(selectedNode);
      if (selectedNode.type === 'decision' && !activeDecisions.some(n => n.id === selectedNode.id)) activeDecisions.unshift(selectedNode);
    }

    // Connection-Driven & Document-Tree Layout Engine
    // Instead of sticking nodes into static arbitrary slots, nodes align with their real parent/child connections!
    const edges = graphData?.edges || [];
    const CARD_SPACING = 118;
    const START_Y = 40;

    const isDocMode = lineageGranularity === 'document';
    const X_SOURCE = 50;
    const X_DOC = 390;
    const X_CLAIM = 730;
    const X_CONFLICT = isDocMode ? 730 : 1070;
    const X_DECISION = isDocMode ? 1070 : 1410;

    // 1. Position Sources (Column 0)
    activeSources.forEach((src, idx) => {
      map[src.id] = {
        x: X_SOURCE,
        y: START_Y + idx * (CARD_SPACING * 1.5)
      };
    });

    // 2. Position Documents based on their parent Sources (Column 1)
    const docsBySource = {};
    const unparentedDocs = [];

    activeDocs.forEach(doc => {
      let parentSrcId = null;
      edges.forEach(e => {
        if (e.target === doc.id && e.source.startsWith('src_')) parentSrcId = e.source;
      });
      if (parentSrcId && map[parentSrcId]) {
        if (!docsBySource[parentSrcId]) docsBySource[parentSrcId] = [];
        docsBySource[parentSrcId].push(doc);
      } else {
        unparentedDocs.push(doc);
      }
    });

    let currentDocY = START_Y;
    activeSources.forEach(src => {
      const childDocs = docsBySource[src.id] || [];
      const srcPos = map[src.id];
      if (childDocs.length > 0) {
        const totalHeight = (childDocs.length - 1) * CARD_SPACING;
        const startDocY = Math.max(START_Y, (srcPos?.y || START_Y) - totalHeight / 2);
        childDocs.forEach((doc, idx) => {
          const docY = startDocY + idx * CARD_SPACING;
          map[doc.id] = { x: X_DOC, y: docY };
          currentDocY = Math.max(currentDocY, docY + CARD_SPACING);
        });
      }
    });

    unparentedDocs.forEach((doc, idx) => {
      map[doc.id] = { x: X_DOC, y: currentDocY + idx * CARD_SPACING };
    });

    // 3. Position Claims based on their parent Document (Column 2)
    const claimsByDoc = {};
    const unparentedClaims = [];

    activeClaims.forEach(cl => {
      let parentDocId = cl.docId || null;
      if (!parentDocId) {
        edges.forEach(e => {
          if (e.target === cl.id && e.source.startsWith('doc_')) parentDocId = e.source;
        });
      }
      if (parentDocId && map[parentDocId]) {
        if (!claimsByDoc[parentDocId]) claimsByDoc[parentDocId] = [];
        claimsByDoc[parentDocId].push(cl);
      } else {
        unparentedClaims.push(cl);
      }
    });

    let currentClaimY = START_Y;
    activeDocs.forEach(doc => {
      const childClaims = claimsByDoc[doc.id] || [];
      const docPos = map[doc.id];
      if (childClaims.length > 0) {
        const totalHeight = (childClaims.length - 1) * (CARD_SPACING * 0.92);
        const startClaimY = Math.max(START_Y, (docPos?.y || START_Y) - totalHeight / 2);
        childClaims.forEach((cl, idx) => {
          const claimY = startClaimY + idx * (CARD_SPACING * 0.92);
          map[cl.id] = { x: X_CLAIM, y: claimY };
          currentClaimY = Math.max(currentClaimY, claimY + CARD_SPACING);
        });
      }
    });

    unparentedClaims.forEach((cl, idx) => {
      map[cl.id] = { x: X_CLAIM, y: currentClaimY + idx * CARD_SPACING };
    });

    // 4. Position Conflicts based on their connected claims or documents (Column 3 or Column 2 in Doc Mode)
    activeConflicts.forEach((c, idx) => {
      const cItem = conflictMap[c.id];
      let yAnchor = null;
      if (cItem?.claimAId && cItem?.claimBId && map[cItem.claimAId] && map[cItem.claimBId]) {
        yAnchor = (map[cItem.claimAId].y + map[cItem.claimBId].y) / 2;
      } else {
        const docYs = [];
        edges.forEach(e => {
          if (e.target === c.id && map[e.source]) docYs.push(map[e.source].y);
        });
        if (docYs.length >= 2) {
          yAnchor = (docYs[0] + docYs[1]) / 2;
        }
      }

      const assignedY = yAnchor !== null ? yAnchor : START_Y + idx * (CARD_SPACING * 1.15);
      map[c.id] = { x: X_CONFLICT, y: assignedY };
    });

    // 5. Position Decisions based on their grounding claims or conflicts (Column 4 or Column 3 in Doc Mode)
    activeDecisions.forEach((dec, idx) => {
      const parentYs = [];
      edges.forEach(e => {
        if (e.target === dec.id && map[e.source]) {
          parentYs.push(map[e.source].y);
        }
      });

      let decY = START_Y + idx * (CARD_SPACING * 1.15);
      if (parentYs.length > 0) {
        decY = parentYs.reduce((a, b) => a + b, 0) / parentYs.length;
      }
      map[dec.id] = { x: X_DECISION, y: decY };
    });

    // Relaxation Pass: Prevent any overlapping nodes within the same column
    const columns = [
      activeSources.map(n => n.id),
      activeDocs.map(n => n.id),
      activeClaims.map(n => n.id),
      activeConflicts.map(n => n.id),
      activeDecisions.map(n => n.id)
    ];

    const MIN_GAP = 96;
    columns.forEach(colNodeIds => {
      const colNodes = colNodeIds.filter(id => !!map[id]).map(id => ({ id, ...map[id] }));
      colNodes.sort((a, b) => a.y - b.y);

      for (let i = 1; i < colNodes.length; i++) {
        const prev = colNodes[i - 1];
        const curr = colNodes[i];
        if (curr.y < prev.y + MIN_GAP) {
          curr.y = prev.y + MIN_GAP;
          map[curr.id].y = curr.y;
        }
      }
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
    conflictMap,
    graphData,
    lineageGranularity
  ]);

  // Merged positions (custom user drags take precedence)
  const nodePositions = useMemo(() => {
    return { ...defaultPositions, ...customPositions };
  }, [defaultPositions, customPositions]);

  // Filter rendered nodes based on calculated positions
  const renderedNodes = useMemo(() => {
    if (!filteredNodes) return [];
    const base = filteredNodes.filter(n => !!nodePositions[n.id]);
    if (nodePositions['cluster_overflow_claims'] && !base.some(n => n.id === 'cluster_overflow_claims')) {
      const claimsCount = filteredNodes.filter(n => n.type === 'claim').length;
      base.push({
        id: 'cluster_overflow_claims',
        type: 'density_cluster',
        label: `+${Math.max(1, claimsCount - 11)} More Claims`,
        count: Math.max(1, claimsCount - 11),
        desc: 'Click to expand full column density'
      });
    }
    return base;
  }, [filteredNodes, nodePositions]);

  // Directional Bezier Connecting Edges
  const renderedEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    const allEdges = [...graphData.edges];

    // Add synthesized cluster edges from parent documents to claim clusters
    filteredNodes.forEach(n => {
      if (n.type === 'claim_cluster' && n.docId && n.docId !== 'general') {
        allEdges.push({
          id: `cluster_edge_${n.docId}_${n.id}`,
          source: n.docId,
          target: n.id,
          type: 'hierarchy'
        });
      }
    });

    // In document mode, synthesize direct Document -> Conflict and Conflict -> Decision edges
    if (lineageGranularity === 'document') {
      conflictsList.forEach(c => {
        const cItem = conflictMap[c.id];
        let docAId = null;
        let docBId = null;
        if (cItem?.claimAId) {
          graphData.edges.forEach(e => {
            if (e.target === cItem.claimAId && e.source.startsWith('doc_')) docAId = e.source;
          });
        }
        if (cItem?.claimBId) {
          graphData.edges.forEach(e => {
            if (e.target === cItem.claimBId && e.source.startsWith('doc_')) docBId = e.source;
          });
        }
        if (docAId && nodePositions[docAId] && nodePositions[c.id] && !nodePositions[cItem.claimAId]) {
          allEdges.push({
            id: `synth_doc_${docAId}_cfl_${c.id}`,
            source: docAId,
            target: c.id,
            type: 'conflict',
            isConflictConnection: true
          });
        }
        if (docBId && nodePositions[docBId] && nodePositions[c.id] && !nodePositions[cItem.claimBId]) {
          allEdges.push({
            id: `synth_doc_${docBId}_cfl_${c.id}`,
            source: docBId,
            target: c.id,
            type: 'conflict',
            isConflictConnection: true
          });
        }
      });

      decisionsList.forEach(dec => {
        graphData.edges.forEach(e => {
          if (e.target === dec.id) {
            conflictsList.forEach(c => {
              const cItem = conflictMap[c.id];
              if (cItem?.claimAId === e.source || cItem?.claimBId === e.source) {
                if (nodePositions[c.id] && nodePositions[dec.id]) {
                  allEdges.push({
                    id: `synth_cfl_${c.id}_dec_${dec.id}`,
                    source: c.id,
                    target: dec.id,
                    type: 'decision_grounding'
                  });
                }
              }
            });
          }
        });
      });
    }

    return allEdges
      .filter(e => nodePositions[e.source] && nodePositions[e.target])
      .map(e => {
        const src = nodePositions[e.source];
        const tgt = nodePositions[e.target];

        // Professional port-to-port bezier routing
        const isForward = tgt.x >= src.x + 30;
        let x1, y1, x2, y2, dx;

        if (isForward) {
          x1 = src.x + CARD_WIDTH;
          y1 = src.y + CARD_HEIGHT / 2;
          x2 = tgt.x;
          y2 = tgt.y + CARD_HEIGHT / 2;
          dx = Math.max(50, (x2 - x1) * 0.45);
        } else {
          x1 = src.x;
          y1 = src.y + CARD_HEIGHT / 2;
          x2 = tgt.x + CARD_WIDTH;
          y2 = tgt.y + CARD_HEIGHT / 2;
          dx = Math.max(50, Math.abs(x2 - x1) * 0.45);
        }

        const pathData = `M ${x1} ${y1} C ${x1 + (isForward ? dx : -dx)} ${y1}, ${x2 - (isForward ? dx : -dx)} ${y2}, ${x2} ${y2}`;
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
  }, [graphData, nodePositions, connectedNodeMap, selectedConflictId, filteredNodes, lineageGranularity, conflictsList, decisionsList, conflictMap]);

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

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (selectedConflictId !== 'all') count++;
    if (selectedDocFilter !== 'all') count++;
    if (filterSeverity !== 'all') count++;
    if (filterStatus !== 'all') count++;
    if (filterClaimTrust !== 'all') count++;
    if (showOnlyConflicted) count++;
    if (displayLimit !== 12) count++;
    if (searchQuery.trim() !== '') count++;
    if (visibleTiers.size < 5) count++;
    return count;
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
      
      {/* Unified Executive Lineage Command Card (Single Card Container) */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '10px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.02)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        width: '100%',
        boxSizing: 'border-box'
      }}>
        {/* Row 1: Primary Toolbar Controls */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '6px',
          padding: '5px 10px',
          background: '#FAFAFA'
        }}>
          {/* Left: Asset Focus & Workspace Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.68rem', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.02em' }}>
              Asset:
            </span>

            <select
              value={selectedNodeId || ''}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedNodeId(val);
                if (val) {
                  setCausalSubgraphOnly(true);
                  showToast?.("Loaded direct 2-hop causal path");
                }
                if (viewMode === 'conflicts') setViewMode('focused');
              }}
              style={{
                padding: '2px 6px',
                borderRadius: '5px',
                border: '1px solid #CBD5E1',
                background: '#FFFFFF',
                fontSize: '0.72rem',
                fontWeight: 600,
                color: '#0F172A',
                cursor: 'pointer',
                maxWidth: '220px',
                outline: 'none',
                height: '26px'
              }}
            >
              {(!graphData?.nodes || graphData.nodes.length === 0) ? (
                <option value="">No assets ingested</option>
              ) : (
                graphData.nodes.map(n => (
                  <option key={n.id} value={n.id}>
                    [{n.type.toUpperCase()}] {n.label}
                  </option>
                ))
              )}
            </select>

            {/* Departmental Workspace Pill */}
            {activeWorkspace && (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px',
                padding: '2px 6px',
                borderRadius: '5px',
                background: activeWorkspace.id !== 'all' && !lineageScopeAll ? '#EFF6FF' : '#F1F5F9',
                border: `1px solid ${activeWorkspace.id !== 'all' && !lineageScopeAll ? '#BFDBFE' : '#E2E8F0'}`,
                fontSize: '0.68rem',
                fontWeight: 700,
                color: activeWorkspace.id !== 'all' && !lineageScopeAll ? '#1D4ED8' : '#475569',
                height: '26px',
                boxSizing: 'border-box'
              }}>
                <span>{activeWorkspace.icon || '🏢'}</span>
                <span>{lineageScopeAll ? 'Unified All' : activeWorkspace.name}</span>
                {activeWorkspace.id !== 'all' && !lineageScopeAll && (
                  <span style={{ fontSize: '0.60rem', color: '#16A34A', background: '#DCFCE7', padding: '0 3px', borderRadius: '3px' }}>
                    Isolated
                  </span>
                )}
              </span>
            )}
          </div>

          {/* Document-Level vs Claim-Level Granularity Switcher */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '2px',
            background: '#F8FAFC',
            padding: '2px',
            borderRadius: '6px',
            border: '1px solid #CBD5E1'
          }}>
            <button
              type="button"
              onClick={() => {
                setLineageGranularity('document');
                showToast?.("Document Flow: Macro policy lineage");
              }}
              style={{
                padding: '2px 8px',
                fontSize: '0.68rem',
                fontWeight: 700,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: lineageGranularity === 'document' ? '#0284C7' : 'transparent',
                color: lineageGranularity === 'document' ? '#FFFFFF' : '#475569',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '24px',
                boxShadow: lineageGranularity === 'document' ? '0 1px 2px rgba(2,132,199,0.25)' : 'none',
                transition: 'all 0.15s ease'
              }}
              title="Document-Level Lineage: Clean system-to-policy flow without claim clutter"
            >
              <FileText size={11} />
              <span>Document Flow</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setLineageGranularity('claim');
                showToast?.("Claim Provenance: Granular atomic assertions");
              }}
              style={{
                padding: '2px 8px',
                fontSize: '0.68rem',
                fontWeight: 700,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: lineageGranularity === 'claim' ? '#059669' : 'transparent',
                color: lineageGranularity === 'claim' ? '#FFFFFF' : '#475569',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '24px',
                boxShadow: lineageGranularity === 'claim' ? '0 1px 2px rgba(5,150,105,0.25)' : 'none',
                transition: 'all 0.15s ease'
              }}
              title="Claim-Level Lineage: Granular atomic assertions drill-down"
            >
              <Zap size={11} />
              <span>Claim Provenance</span>
            </button>
          </div>

          {/* Center: Minimal Segmented Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px', background: '#F1F5F9', padding: '2px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
            <button
              onClick={() => {
                setViewMode('conflicts');
                const firstConf = conflictsList[0];
                if (firstConf) setSelectedNodeId(firstConf.id);
              }}
              style={{
                padding: '3px 8px',
                fontSize: '0.69rem',
                fontWeight: 700,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: viewMode === 'conflicts' ? '#EA580C' : 'transparent',
                color: viewMode === 'conflicts' ? '#FFFFFF' : '#475569',
                boxShadow: viewMode === 'conflicts' ? '0 1px 2px rgba(234,88,12,0.25)' : 'none',
                transition: 'all 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '24px'
              }}
              title="Focus on contradictions"
            >
              <Zap size={11} />
              <span>Contradictions ({conflictsList.length})</span>
            </button>

            <button
              onClick={() => setViewMode('focused')}
              style={{
                padding: '3px 8px',
                fontSize: '0.69rem',
                fontWeight: 700,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: viewMode === 'focused' ? '#2563EB' : 'transparent',
                color: viewMode === 'focused' ? '#FFFFFF' : '#475569',
                boxShadow: viewMode === 'focused' ? '0 1px 2px rgba(37,99,235,0.25)' : 'none',
                transition: 'all 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '24px'
              }}
              title="Focus on active node path"
            >
              <Eye size={11} />
              <span>Focus</span>
            </button>

            <button
              onClick={() => setViewMode('all')}
              style={{
                padding: '3px 8px',
                fontSize: '0.69rem',
                fontWeight: 700,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: viewMode === 'all' ? '#0284C7' : 'transparent',
                color: viewMode === 'all' ? '#FFFFFF' : '#475569',
                boxShadow: viewMode === 'all' ? '0 1px 2px rgba(2,132,199,0.25)' : 'none',
                transition: 'all 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '24px'
              }}
              title="Full overview DAG"
            >
              <Database size={11} />
              <span>Overview</span>
            </button>
          </div>

          {/* Right: Minimal Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <button
              onClick={() => setIsFilterPanelOpen(prev => !prev)}
              style={{
                padding: '3px 8px',
                fontSize: '0.70rem',
                fontWeight: 700,
                borderRadius: '5px',
                border: activeFilterCount > 0 ? '1px solid #EA580C' : '1px solid #CBD5E1',
                background: isFilterPanelOpen || activeFilterCount > 0 ? '#FFF7ED' : '#FFFFFF',
                color: isFilterPanelOpen || activeFilterCount > 0 ? '#EA580C' : '#334155',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '26px'
              }}
              title="Toggle Filters"
            >
              <Sliders size={11} />
              <span>Filters</span>
              {activeFilterCount > 0 && (
                <span style={{
                  background: '#EA580C',
                  color: '#FFFFFF',
                  borderRadius: '6px',
                  padding: '0 3px',
                  fontSize: '0.60rem',
                  fontWeight: 800
                }}>
                  {activeFilterCount}
                </span>
              )}
              <ChevronDown size={10} style={{ transform: isFilterPanelOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }} />
            </button>

            <button
              onClick={() => setIsDrawerOpen(true)}
              style={{
                padding: '3px 8px',
                fontSize: '0.70rem',
                fontWeight: 600,
                borderRadius: '5px',
                border: '1px solid #CBD5E1',
                background: '#FFFFFF',
                color: '#334155',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '26px'
              }}
              title="Claims Drawer"
            >
              <FileText size={11} />
              <span>Claims ({graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0})</span>
            </button>

            <button
              onClick={() => setIsImpactReportOpen(true)}
              style={{
                padding: '3px 8px',
                fontSize: '0.70rem',
                fontWeight: 700,
                borderRadius: '5px',
                border: '1px solid #7C3AED',
                background: isImpactReportOpen ? '#7C3AED' : '#FAF5FF',
                color: isImpactReportOpen ? '#FFFFFF' : '#7C3AED',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '26px',
                boxShadow: isImpactReportOpen ? '0 1px 3px rgba(124,58,237,0.3)' : 'none',
                transition: 'all 0.15s ease'
              }}
              title="Open Atlan-style Proactive Impact & Blast Radius Report"
            >
              <BarChart3 size={11} />
              <span>Impact Report</span>
            </button>

            <button
              onClick={fetchLineage}
              disabled={loading}
              style={{
                padding: '3px 7px',
                fontSize: '0.70rem',
                fontWeight: 600,
                borderRadius: '5px',
                border: '1px solid #CBD5E1',
                background: '#FFFFFF',
                color: '#334155',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                height: '26px'
              }}
              title="Refresh Graph"
            >
              <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>

        {/* Row 2: Integrated Filter Section (Inside the SAME Card) */}
        {isFilterPanelOpen && (
          <div style={{
            borderTop: '1px solid #E2E8F0',
            padding: '6px 10px',
            background: '#FFFFFF',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px'
          }}>
            {/* Filter Selects Strip */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              flexWrap: 'wrap'
            }}>
              {/* Conflict Selector */}
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#EA580C', textTransform: 'uppercase' }}>
                  Conflict:
                </span>
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
                    padding: '2px 5px',
                    borderRadius: '4px',
                    border: selectedConflictId !== 'all' ? '1px solid #EA580C' : '1px solid #CBD5E1',
                    background: selectedConflictId !== 'all' ? '#FFF7ED' : '#F8FAFC',
                    fontSize: '0.70rem',
                    fontWeight: selectedConflictId !== 'all' ? 700 : 500,
                    color: selectedConflictId !== 'all' ? '#C2410C' : '#334155',
                    outline: 'none',
                    cursor: 'pointer',
                    height: '24px'
                  }}
                >
                  <option value="all">All ({conflictsList.length})</option>
                  {conflictsList.map((c, i) => (
                    <option key={c.id} value={c.id}>
                      #{i + 1} [{c.severity || 'HIGH'}] {c.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Policy Selector */}
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#0284C7', textTransform: 'uppercase' }}>
                  Policy:
                </span>
                <select
                  value={selectedDocFilter}
                  onChange={(e) => {
                    setSelectedDocFilter(e.target.value);
                    if (e.target.value !== 'all') setSelectedNodeId(e.target.value);
                  }}
                  style={{
                    padding: '2px 5px',
                    borderRadius: '4px',
                    border: selectedDocFilter !== 'all' ? '1px solid #0284C7' : '1px solid #CBD5E1',
                    background: selectedDocFilter !== 'all' ? '#F0F9FF' : '#F8FAFC',
                    fontSize: '0.70rem',
                    fontWeight: selectedDocFilter !== 'all' ? 700 : 500,
                    color: selectedDocFilter !== 'all' ? '#0369A1' : '#334155',
                    outline: 'none',
                    cursor: 'pointer',
                    height: '24px'
                  }}
                >
                  <option value="all">All ({documentsList.length})</option>
                  {documentsList.map(d => (
                    <option key={d.id} value={d.id}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Severity Selector */}
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                  Severity:
                </span>
                <select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value)}
                  style={{
                    padding: '2px 5px',
                    borderRadius: '4px',
                    border: filterSeverity !== 'all' ? '1px solid #2563EB' : '1px solid #CBD5E1',
                    background: filterSeverity !== 'all' ? '#EFF6FF' : '#F8FAFC',
                    fontSize: '0.70rem',
                    color: filterSeverity !== 'all' ? '#1D4ED8' : '#334155',
                    fontWeight: filterSeverity !== 'all' ? 700 : 500,
                    outline: 'none',
                    cursor: 'pointer',
                    height: '24px'
                  }}
                >
                  <option value="all">All</option>
                  <option value="HIGH">High</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="MEDIUM">Med</option>
                  <option value="LOW">Low</option>
                </select>
              </div>

              {/* Trust Selector */}
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#16A34A', textTransform: 'uppercase' }}>
                  Trust:
                </span>
                <select
                  value={filterClaimTrust}
                  onChange={(e) => setFilterClaimTrust(e.target.value)}
                  style={{
                    padding: '2px 5px',
                    borderRadius: '4px',
                    border: filterClaimTrust !== 'all' ? '1px solid #16A34A' : '1px solid #CBD5E1',
                    background: filterClaimTrust !== 'all' ? '#F0FDF4' : '#F8FAFC',
                    fontSize: '0.70rem',
                    color: filterClaimTrust !== 'all' ? '#15803D' : '#334155',
                    fontWeight: filterClaimTrust !== 'all' ? 700 : 500,
                    outline: 'none',
                    cursor: 'pointer',
                    height: '24px'
                  }}
                >
                  <option value="all">All</option>
                  <option value="verified">Verified (≥90%)</option>
                  <option value="review">Review (&lt;90%)</option>
                  <option value="outdated">Outdated</option>
                </select>
              </div>

              {/* Density Selector */}
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                  Density:
                </span>
                <select
                  value={displayLimit}
                  onChange={(e) => setDisplayLimit(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                  style={{
                    padding: '2px 5px',
                    borderRadius: '4px',
                    border: '1px solid #CBD5E1',
                    background: '#F8FAFC',
                    fontSize: '0.70rem',
                    color: '#334155',
                    outline: 'none',
                    cursor: 'pointer',
                    height: '24px'
                  }}
                >
                  <option value={6}>6</option>
                  <option value={12}>12</option>
                  <option value={24}>24</option>
                  <option value="all">All</option>
                </select>
              </div>
            </div>

            {/* Tiers & Status Summary */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '6px',
              borderTop: '1px solid #F1F5F9',
              paddingTop: '4px'
            }}>
              {/* Tiers + Conflicted */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => {
                    setShowOnlyConflicted(prev => !prev);
                    if (!showOnlyConflicted) showToast?.("Focused on contradictory paths");
                  }}
                  style={{
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontSize: '0.66rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    border: showOnlyConflicted ? '1px solid #EA580C' : '1px solid #CBD5E1',
                    background: showOnlyConflicted ? '#EA580C' : '#FFFFFF',
                    color: showOnlyConflicted ? '#FFFFFF' : '#475569',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '3px',
                    height: '22px'
                  }}
                >
                  <AlertTriangle size={10} />
                  <span>Conflicted</span>
                  {showOnlyConflicted && <span>✓</span>}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setGroupCleanClaims(prev => !prev);
                    showToast?.(!groupCleanClaims ? "Anomaly Mode: Clean claims rolled into clusters" : "Expanded all individual claims");
                  }}
                  style={{
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontSize: '0.66rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    border: groupCleanClaims ? '1px solid #059669' : '1px solid #CBD5E1',
                    background: groupCleanClaims ? '#ECFDF5' : '#FFFFFF',
                    color: groupCleanClaims ? '#059669' : '#475569',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '3px',
                    height: '22px'
                  }}
                  title="Group clean, non-conflicting claims into summary clusters to focus exclusively on anomalies"
                >
                  <ShieldCheck size={10} color={groupCleanClaims ? '#059669' : '#64748B'} />
                  <span>Group Clean</span>
                  {groupCleanClaims && <span>✓</span>}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setCausalSubgraphOnly(prev => !prev);
                    showToast?.(!causalSubgraphOnly ? "Causal Trace: Isolated direct 2-hop causal path" : "Showing full enterprise graph");
                  }}
                  style={{
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontSize: '0.66rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    border: causalSubgraphOnly ? '1px solid #2563EB' : '1px solid #CBD5E1',
                    background: causalSubgraphOnly ? '#EFF6FF' : '#FFFFFF',
                    color: causalSubgraphOnly ? '#2563EB' : '#475569',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '3px',
                    height: '22px'
                  }}
                  title="Isolate direct 2-hop causal lineage path (Decisions ➔ Causal Claims ➔ Policies)"
                >
                  <Eye size={10} color={causalSubgraphOnly ? '#2563EB' : '#64748B'} />
                  <span>Causal (k=2)</span>
                  {causalSubgraphOnly && <span>✓</span>}
                </button>

                <span style={{ fontSize: '0.64rem', color: '#94A3B8', margin: '0 1px' }}>Tiers:</span>

                {[
                  { type: 'source', label: 'Src', count: graphData?.nodes?.filter(n => n.type === 'source')?.length || 0, color: '#2563EB' },
                  { type: 'document', label: 'Doc', count: documentsList.length, color: '#0284C7' },
                  { type: 'claim', label: 'Clm', count: graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0, color: '#059669' },
                  { type: 'conflict', label: 'Cfl', count: conflictsList.length, color: '#EA580C' },
                  { type: 'decision', label: 'Dec', count: graphData?.nodes?.filter(n => n.type === 'decision')?.length || 0, color: '#7C3AED' }
                ].map(t => {
                  const isVisible = visibleTiers.has(t.type);
                  return (
                    <button
                      key={t.type}
                      type="button"
                      onClick={() => toggleTier(t.type)}
                      style={{
                        padding: '1px 5px',
                        borderRadius: '4px',
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        border: isVisible ? `1px solid ${t.color}` : '1px solid #E2E8F0',
                        background: isVisible ? `${t.color}15` : '#F8FAFC',
                        color: isVisible ? t.color : '#94A3B8',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '3px',
                        height: '22px',
                        opacity: isVisible ? 1 : 0.6
                      }}
                      title={`Toggle ${t.label}`}
                    >
                      <span>{t.label}</span>
                      <span style={{ fontSize: '0.58rem', fontWeight: 800, background: isVisible ? `${t.color}25` : '#E2E8F0', padding: '0 2px', borderRadius: '2px' }}>
                        {t.count}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Counts & Reset */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.66rem', color: '#64748B' }}>
                  <strong>{renderedNodes.length}</strong> / <strong>{graphData?.nodes?.length || 0}</strong>
                </span>

                {activeFilterCount > 0 && (
                  <button
                    type="button"
                    onClick={resetAllFilters}
                    style={{
                      padding: '1px 5px',
                      borderRadius: '3px',
                      border: '1px solid #FCA5A5',
                      background: '#FEF2F2',
                      color: '#DC2626',
                      fontSize: '0.64rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '2px',
                      height: '22px'
                    }}
                    title="Reset all filters"
                  >
                    <RotateCcw size={9} />
                    <span>Reset</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

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
                <marker id="atlan-arrow-default" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#94A3B8" />
                </marker>
                <marker id="atlan-arrow-active" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#2563EB" />
                </marker>
                <marker id="atlan-arrow-conflict" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#EA580C" />
                </marker>
                <marker id="atlan-arrow-decision" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#7C3AED" />
                </marker>
              </defs>

              {renderedEdges.map(edge => {
                const isConflictLine = edge.type === 'conflict' || edge.isConflictConnection;
                const strokeColor = isConflictLine
                  ? '#EA580C'
                  : edge.isActive
                    ? edge.type === 'decision_grounding' ? '#7C3AED' : '#2563EB'
                    : '#94A3B8';

                const strokeWidth = isConflictLine ? 2.5 : edge.isActive ? 2.2 : 1.75;
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
                      strokeDasharray="none"
                      markerEnd={marker}
                      style={{
                        transition: 'stroke 0.2s ease, stroke-width 0.2s ease'
                      }}
                    />
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

              // Anomaly Roll-up Cluster Card
              if (node.type === 'claim_cluster') {
                return (
                  <div
                    key={node.id}
                    className="atlan-node-card"
                    onClick={() => {
                      setDrawerDocFilter(node.docId || 'all');
                      setIsDrawerOpen(true);
                      showToast?.(`Viewing ${node.count} clean claims from ${node.docTitle}`);
                    }}
                    style={{
                      position: 'absolute',
                      left: `${pos.x}px`,
                      top: `${pos.y}px`,
                      width: `${CARD_WIDTH}px`,
                      height: `${CARD_HEIGHT}px`,
                      background: 'linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)',
                      borderRadius: '10px',
                      border: '1.5px dashed #059669',
                      boxShadow: '0 2px 8px rgba(5,150,105,0.12)',
                      boxSizing: 'border-box',
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      zIndex: 10,
                      userSelect: 'none',
                      transition: 'all 0.15s ease'
                    }}
                    title="Click to view all clean, verified claims in Claims Drawer"
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#166534', background: '#BBF7D0', padding: '1px 6px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <ShieldCheck size={11} /> CLUSTER (CLEAN)
                      </span>
                      <span style={{ fontSize: '0.66rem', color: '#15803D', fontWeight: 700 }}>
                        {node.count} Claims
                      </span>
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '0.78rem', fontWeight: 700, color: '#14532D', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        🛡️ {node.label}
                      </h4>
                      <p style={{ margin: '2px 0 0 0', fontSize: '0.68rem', color: '#166534', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        Source: {node.docTitle}
                      </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(5,150,105,0.2)', paddingTop: '4px', fontSize: '0.65rem', color: '#15803D' }}>
                      <span>Non-Conflicting</span>
                      <span style={{ fontWeight: 700, textDecoration: 'underline' }}>Browse Claims ›</span>
                    </div>
                  </div>
                );
              }

              // High-Density Column Overflow Cluster Card
              if (node.type === 'density_cluster') {
                return (
                  <div
                    key={node.id}
                    className="atlan-node-card"
                    onClick={() => {
                      setDisplayLimit('all');
                      showToast?.("Expanded all claims in column");
                    }}
                    style={{
                      position: 'absolute',
                      left: `${pos.x}px`,
                      top: `${pos.y}px`,
                      width: `${CARD_WIDTH}px`,
                      height: `${CARD_HEIGHT}px`,
                      background: 'linear-gradient(135deg, #F8FAFC 0%, #EEF2F6 100%)',
                      borderRadius: '10px',
                      border: '1.5px dashed #64748B',
                      boxShadow: '0 1px 4px rgba(0,0,0,0.02)',
                      boxSizing: 'border-box',
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      zIndex: 10,
                      userSelect: 'none',
                      transition: 'all 0.15s ease'
                    }}
                    title="Click to expand full column density"
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#334155', background: '#E2E8F0', padding: '1px 6px', borderRadius: '4px' }}>
                        COLUMN OVERFLOW
                      </span>
                      <span style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 700 }}>
                        +{node.count} Hidden
                      </span>
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '0.78rem', fontWeight: 700, color: '#0F172A' }}>
                        {node.label}
                      </h4>
                      <p style={{ margin: '2px 0 0 0', fontSize: '0.68rem', color: '#64748B' }}>
                        {node.desc}
                      </p>
                    </div>
                    <div style={{ borderTop: '1px solid #CBD5E1', paddingTop: '4px', fontSize: '0.66rem', color: '#2563EB', fontWeight: 700, textAlign: 'center' }}>
                      ⚡ Click to Expand All
                    </div>
                  </div>
                );
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
                  {/* Atlan-Style Home / Origin Beacon */}
                  {isSelected && (
                    <div style={{
                      position: 'absolute',
                      top: '-16px',
                      left: '10px',
                      background: '#1D4ED8',
                      color: '#fff',
                      borderRadius: '4px 4px 0 0',
                      padding: '2px 8px',
                      fontSize: '0.62rem',
                      fontWeight: 800,
                      letterSpacing: '0.04em',
                      boxShadow: '0 2px 6px rgba(29,78,216,0.35)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <Home size={10} />
                      <span>YOU ARE HERE</span>
                    </div>
                  )}

                  {/* Left Connection Port: Shows Upstream Parent Count */}
                  {node.type !== 'source' && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNodeId(node.id);
                        setViewMode('focused');
                        setCausalSubgraphOnly(true);
                        showToast?.(`Tracing upstream root causes of ${node.label}`);
                      }}
                      style={{
                        position: 'absolute',
                        left: '-12px',
                        top: 'calc(50% - 9px)',
                        padding: '1px 5px',
                        borderRadius: '8px',
                        background: '#fff',
                        border: `1.5px solid ${borderColor}`,
                        boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '2px',
                        fontSize: '0.58rem',
                        fontWeight: 800,
                        color: borderColor,
                        cursor: 'pointer',
                        zIndex: 25
                      }}
                      title={`${graphData?.edges?.filter(e => e.target === node.id).length || 0} Upstream Dependencies — Click to trace upstream`}
                    >
                      <span>◀</span>
                      <span>{graphData?.edges?.filter(e => e.target === node.id).length || 0}</span>
                    </div>
                  )}

                  {/* Right Connection Port: Shows Downstream Impact Count */}
                  {node.type !== 'decision' && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNodeId(node.id);
                        setViewMode('focused');
                        setCausalSubgraphOnly(true);
                        showToast?.(`Tracing downstream blast radius of ${node.label}`);
                      }}
                      style={{
                        position: 'absolute',
                        right: '-12px',
                        top: 'calc(50% - 9px)',
                        padding: '1px 5px',
                        borderRadius: '8px',
                        background: '#fff',
                        border: `1.5px solid ${borderColor}`,
                        boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '2px',
                        fontSize: '0.58rem',
                        fontWeight: 800,
                        color: borderColor,
                        cursor: 'pointer',
                        zIndex: 25
                      }}
                      title={`${graphData?.edges?.filter(e => e.source === node.id).length || 0} Downstream Impacts — Click to trace blast radius`}
                    >
                      <span>{graphData?.edges?.filter(e => e.source === node.id).length || 0}</span>
                      <span>▶</span>
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
                    {node.type === 'document' ? (
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          setLineageGranularity('claim');
                          setSelectedDocFilter(node.id);
                          showToast?.(`Drilled down to claims for ${node.label}`);
                        }}
                        style={{
                          color: '#0284c7',
                          fontWeight: 700,
                          fontSize: '0.64rem',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '2px',
                          background: '#f0f9ff',
                          padding: '1px 5px',
                          borderRadius: '4px'
                        }}
                        title="Drill down to atomic claims (Atlan Column-Level Lineage)"
                      >
                        <span>View Claims &rsaquo;</span>
                      </span>
                    ) : (
                      <span style={{ color: '#2563eb', fontWeight: 600, fontSize: '0.62rem' }}>
                        view lineage &rsaquo;
                      </span>
                    )}
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

      {/* 5. Atlan-Style Proactive Impact Analysis & Blast Radius Drawer */}
      {isImpactReportOpen && (
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
          animation: 'fadeIn 0.15s ease'
        }}>
          <div style={{
            width: '600px',
            maxWidth: '92vw',
            height: '100%',
            background: '#ffffff',
            boxShadow: '-8px 0 32px rgba(0,0,0,0.15)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* Header */}
            <div style={{
              padding: '16px 22px',
              borderBottom: '1px solid #E2E8F0',
              background: '#FAFAFA',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.66rem', fontWeight: 800, color: '#7C3AED', background: '#F5F3FF', padding: '1px 6px', borderRadius: '4px', textTransform: 'uppercase' }}>
                    ATLAN IMPACT ENGINE
                  </span>
                  <span style={{ fontSize: '0.64rem', color: '#16A34A', fontWeight: 700, background: '#DCFCE7', padding: '1px 6px', borderRadius: '4px' }}>
                    Live Blast Radius
                  </span>
                </div>
                <h3 style={{ margin: '4px 0 0 0', fontSize: '1.05rem', fontWeight: 800, color: '#0F172A' }}>
                  Proactive Impact & Root Cause Analysis
                </h3>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <button
                  onClick={() => {
                    const targetNode = selectedNode || graphData?.nodes?.[0];
                    const rows = [
                      ['Asset ID', 'Asset Type', 'Label', 'Relationship', 'Trust Score'],
                      [targetNode?.id, targetNode?.type, targetNode?.label, 'TARGET_ENTITY', targetNode?.trustScore || 'N/A'],
                      ...Array.from(connectedNodeMap.up).map(id => {
                        const n = graphData?.nodes?.find(x => x.id === id);
                        return [id, n?.type, n?.label, 'UPSTREAM_ROOT_CAUSE', n?.trustScore || 'N/A'];
                      }),
                      ...Array.from(connectedNodeMap.down).map(id => {
                        const n = graphData?.nodes?.find(x => x.id === id);
                        return [id, n?.type, n?.label, 'DOWNSTREAM_BLAST_RADIUS', n?.trustScore || 'N/A'];
                      })
                    ];
                    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.map(cell => `"${cell || ''}"`).join(",")).join("\n");
                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement("a");
                    link.setAttribute("href", encodedUri);
                    link.setAttribute("download", `trulin_impact_report_${targetNode?.id || 'export'}.csv`);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    showToast?.("Exported Impact Analysis Report to CSV");
                  }}
                  style={{
                    padding: '4px 9px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    background: '#FFFFFF',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    color: '#334155',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title="Export Impact Report as CSV"
                >
                  <Download size={12} />
                  <span>CSV</span>
                </button>

                <button
                  onClick={() => {
                    const targetNode = selectedNode || graphData?.nodes?.[0];
                    const text = `Trulin Impact Analysis for ${targetNode?.label} (${targetNode?.type})\nUpstream Roots: ${connectedNodeMap.up.size} assets\nDownstream Blast Radius: ${connectedNodeMap.down.size} decisions/systems affected\nActive Conflicts: ${conflictsList.length}`;
                    navigator.clipboard.writeText(text);
                    showToast?.("Copied Impact Summary to Clipboard");
                  }}
                  style={{
                    padding: '4px 9px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    background: '#FFFFFF',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    color: '#334155',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title="Copy Report Summary for Slack / Jira"
                >
                  <Share2 size={12} />
                  <span>Copy</span>
                </button>

                <button
                  onClick={() => setIsImpactReportOpen(false)}
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    background: '#FFFFFF',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#64748B'
                  }}
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Scrollable Report Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Target Entity Overview */}
              {(() => {
                const target = selectedNode || graphData?.nodes?.[0];
                if (!target) return null;
                const upstreamCount = graphData?.edges?.filter(e => e.target === target.id).length || 0;
                const downstreamCount = graphData?.edges?.filter(e => e.source === target.id).length || 0;

                return (
                  <div style={{
                    padding: '14px 16px',
                    borderRadius: '10px',
                    border: '1.5px solid #2563EB',
                    background: 'linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%)',
                    boxShadow: '0 2px 8px rgba(37,99,235,0.08)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#1D4ED8', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <Home size={11} /> TARGET INVESTIGATED ASSET
                      </span>
                      <span style={{ fontSize: '0.64rem', fontWeight: 700, color: '#64748B' }}>
                        ID: <code>{target.id}</code>
                      </span>
                    </div>

                    <h4 style={{ margin: '0 0 6px 0', fontSize: '0.92rem', fontWeight: 800, color: '#0F172A' }}>
                      {target.label}
                    </h4>
                    {target.fullText && (
                      <p style={{ margin: '0 0 10px 0', fontSize: '0.78rem', color: '#475569', lineHeight: 1.45 }}>
                        "{target.fullText}"
                      </p>
                    )}

                    {/* Stats Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', paddingTop: '10px', borderTop: '1px solid #DBEAFE' }}>
                      <div style={{ background: '#FFFFFF', padding: '8px 10px', borderRadius: '6px', border: '1px solid #BFDBFE' }}>
                        <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 700 }}>UPSTREAM ROOTS</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#1D4ED8' }}>{upstreamCount}</div>
                      </div>
                      <div style={{ background: '#FFFFFF', padding: '8px 10px', borderRadius: '6px', border: '1px solid #BFDBFE' }}>
                        <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 700 }}>DOWNSTREAM IMPACT</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#7C3AED' }}>{downstreamCount}</div>
                      </div>
                      <div style={{ background: '#FFFFFF', padding: '8px 10px', borderRadius: '6px', border: '1px solid #BFDBFE' }}>
                        <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 700 }}>BAYESIAN TRUST</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 900, color: (target.trustScore || 0.9) >= 0.85 ? '#16A34A' : '#EA580C' }}>
                          {((target.trustScore || 0.92) * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* 1. Root Cause Analysis (Upstream Dependencies) */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.84rem', fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span>🔌</span> Upstream Root Causes ({connectedNodeMap.up.size})
                  </h4>
                  <span style={{ fontSize: '0.68rem', color: '#64748B' }}>Where this asset originates</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {Array.from(connectedNodeMap.up).length === 0 ? (
                    <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '6px', fontSize: '0.74rem', color: '#94A3B8', textAlign: 'center' }}>
                      No direct upstream dependencies identified.
                    </div>
                  ) : (
                    Array.from(connectedNodeMap.up).map(id => {
                      const n = graphData?.nodes?.find(x => x.id === id);
                      if (!n) return null;
                      return (
                        <div key={id} style={{
                          padding: '8px 12px',
                          borderRadius: '6px',
                          border: '1px solid #E2E8F0',
                          background: '#FFFFFF',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}>
                          <div>
                            <span style={{ fontSize: '0.62rem', fontWeight: 800, color: '#2563EB', background: '#EFF6FF', padding: '1px 5px', borderRadius: '3px', marginRight: '6px' }}>
                              {n.type.toUpperCase()}
                            </span>
                            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#1E293B' }}>
                              {n.label}
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              setSelectedNodeId(n.id);
                              setViewMode('focused');
                              setIsImpactReportOpen(false);
                              showToast?.(`Focused on ${n.label}`);
                            }}
                            style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              border: '1px solid #CBD5E1',
                              background: '#F8FAFC',
                              fontSize: '0.66rem',
                              fontWeight: 700,
                              color: '#2563EB',
                              cursor: 'pointer'
                            }}
                          >
                            Trace
                          </button>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* 2. Active Policy Contradictions */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.84rem', fontWeight: 800, color: '#EA580C', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span>⚖️</span> Active Contradictions & Rule Clashes ({conflictsList.length})
                  </h4>
                  <span style={{ fontSize: '0.68rem', color: '#64748B' }}>Requires human verification</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {conflictsList.slice(0, 5).map((c, i) => (
                    <div key={c.id} style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1.5px solid #EA580C',
                      background: '#FFF7ED',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '5px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#C2410C', background: '#FFEDD5', padding: '1px 6px', borderRadius: '4px' }}>
                          #{i + 1} [{c.severity || 'HIGH'}]
                        </span>
                        <span style={{ fontSize: '0.64rem', color: '#9A3412', fontWeight: 700 }}>
                          {c.status || 'REVIEW_NEEDED'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#9A3412' }}>
                        {c.label}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #FED7AA', paddingTop: '4px' }}>
                        <button
                          onClick={() => {
                            setSelectedConflictId(c.id);
                            setSelectedNodeId(c.id);
                            setViewMode('conflicts');
                            setIsImpactReportOpen(false);
                            showToast?.(`Spotlighted Contradiction #${i + 1}`);
                          }}
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            border: '1px solid #EA580C',
                            background: '#EA580C',
                            color: '#FFFFFF',
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          Spotlight Conflict in DAG
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 3. Downstream Blast Radius (Impacted AI Decisions & Agents) */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.84rem', fontWeight: 800, color: '#7C3AED', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span>🤖</span> Downstream Blast Radius ({connectedNodeMap.down.size})
                  </h4>
                  <span style={{ fontSize: '0.68rem', color: '#64748B' }}>AI decisions & workflows influenced</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {Array.from(connectedNodeMap.down).length === 0 ? (
                    <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '6px', fontSize: '0.74rem', color: '#94A3B8', textAlign: 'center' }}>
                      No direct downstream decisions identified.
                    </div>
                  ) : (
                    Array.from(connectedNodeMap.down).map(id => {
                      const n = graphData?.nodes?.find(x => x.id === id);
                      if (!n) return null;
                      return (
                        <div key={id} style={{
                          padding: '8px 12px',
                          borderRadius: '6px',
                          border: '1px solid #E2E8F0',
                          background: '#FFFFFF',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}>
                          <div>
                            <span style={{ fontSize: '0.62rem', fontWeight: 800, color: '#7C3AED', background: '#FAF5FF', padding: '1px 5px', borderRadius: '3px', marginRight: '6px' }}>
                              {n.type.toUpperCase()}
                            </span>
                            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#1E293B' }}>
                              {n.label}
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              setSelectedNodeId(n.id);
                              setViewMode('focused');
                              setIsImpactReportOpen(false);
                              showToast?.(`Focused on decision ${n.label}`);
                            }}
                            style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              border: '1px solid #7C3AED',
                              background: '#FAF5FF',
                              fontSize: '0.66rem',
                              fontWeight: 700,
                              color: '#7C3AED',
                              cursor: 'pointer'
                            }}
                          >
                            Inspect
                          </button>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

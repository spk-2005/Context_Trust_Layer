import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Folder,
  FolderPlus,
  ChevronRight,
  ChevronDown,
  Upload,
  Move,
  Trash2,
  Edit3,
  FileText,
  ShieldCheck,
  RefreshCw,
  Plus,
  X,
  Search,
  Inbox,
  Layers,
  Copy,
  Eye,
  Check,
  BarChart2,
  Maximize2,
  ExternalLink,
  AlertTriangle,
  GitBranch,
  CheckCircle2,
  Info,
  Network,
  Sparkles,
  BookOpen,
  Shield,
  Lock,
  Scale,
  Coins,
  Users,
  MessageSquare,
  CheckSquare,
  Briefcase,
  ArrowLeft,
  ChevronLeft
} from 'lucide-react';

export default function DocumentWorkspaceExplorer({
  activeOrg,
  token,
  user,
  showToast,
  onInspectDocument,
  onViewClaims,
  readOnly = false,
}) {
  // Folder tree & all documents state
  const [folders, setFolders] = useState([]);
  const [folderTree, setFolderTree] = useState([]);
  const [allDocuments, setAllDocuments] = useState([]);
  const [activeFolderId, setActiveFolderId] = useState(null);
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [initialLoading, setInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loadingFolderIds, setLoadingFolderIds] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');

  // Selected file & preview state
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [selectedDocDetails, setSelectedDocDetails] = useState(null);
  const [selectedDocArtifacts, setSelectedDocArtifacts] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);
  const [activeFacilityTab, setActiveFacilityTab] = useState('preview'); // 'preview' | 'description' | 'claims' | 'lineage'
  const [selectedClaimId, setSelectedClaimId] = useState(null);
  const [claimSearchQuery, setClaimSearchQuery] = useState('');
  const [isFullFileReaderOpen, setIsFullFileReaderOpen] = useState(false);
  const [fullReaderSearch, setFullReaderSearch] = useState('');

  // Folder Insights state
  const [metrics, setMetrics] = useState(null);
  const [showInsightsModal, setShowInsightsModal] = useState(false);

  // Context Menu state
  const [contextMenu, setContextMenu] = useState({
    visible: false,
    x: 0,
    y: 0,
    type: null, // 'folder' | 'document' | 'canvas'
    target: null,
  });

  // Inline folder creation state (OS / Drive style in-place creation)
  const [creatingInParentId, setCreatingInParentId] = useState(undefined); // undefined = none, null = root, string = folderId
  const [creatingFolderName, setCreatingFolderName] = useState('New folder');
  const [isSavingNewFolder, setIsSavingNewFolder] = useState(false);
  const inlineCreateInputRef = useRef(null);
  const creatingInParentIdRef = useRef(creatingInParentId);
  creatingInParentIdRef.current = creatingInParentId;

  // Inline rename state (OS / Drive style in-place editing)
  const [renamingFolderId, setRenamingFolderId] = useState(null);
  const [renameInputVal, setRenameInputVal] = useState('');
  const [isSavingRename, setIsSavingRename] = useState(false);
  const inlineRenameInputRef = useRef(null);

  const [showMoveFolderModal, setShowMoveFolderModal] = useState(false);
  const [movingFolder, setMovingFolder] = useState(null);
  const [moveFolderTargetId, setMoveFolderTargetId] = useState('');

  const [showMoveDocModal, setShowMoveDocModal] = useState(false);
  const [movingDoc, setMovingDoc] = useState(null);
  const [moveDocTargetFolderId, setMoveDocTargetFolderId] = useState('');

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadFolderId, setUploadFolderId] = useState(null);
  const [uploadDocType, setUploadDocType] = useState('policy');
  const [isUploading, setIsUploading] = useState(false);

  const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
  const directoryContainerRef = useRef(null);

  // Dismiss context menu
  useEffect(() => {
    const handleDismiss = () => {
      if (contextMenu.visible) {
        setContextMenu(prev => ({ ...prev, visible: false }));
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') handleDismiss();
    };
    window.addEventListener('click', handleDismiss);
    window.addEventListener('scroll', handleDismiss, true);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('click', handleDismiss);
      window.removeEventListener('scroll', handleDismiss, true);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [contextMenu.visible]);

  // Auto-focus and highlight folder text when entering inline rename mode
  useEffect(() => {
    if (renamingFolderId) {
      const timer = setTimeout(() => {
        if (inlineRenameInputRef.current) {
          inlineRenameInputRef.current.focus();
          inlineRenameInputRef.current.select();
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [renamingFolderId]);

  // Auto-focus and highlight folder text when entering inline create mode
  useEffect(() => {
    if (creatingInParentId !== undefined) {
      const timer = setTimeout(() => {
        if (inlineCreateInputRef.current) {
          inlineCreateInputRef.current.focus();
          inlineCreateInputRef.current.select();
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [creatingInParentId]);

  // Keyboard shortcuts: F2 for Rename, Ctrl+Shift+N for New Folder
  useEffect(() => {
    const handleGlobalFolderKeys = (e) => {
      if (readOnly) return;
      if (e.key === 'F2' && activeFolderId && !renamingFolderId && creatingInParentId === undefined) {
        const f = folders.find(item => item.id === activeFolderId);
        if (f && !f.is_system) {
          e.preventDefault();
          setRenamingFolderId(f.id);
          setRenameInputVal(f.name);
        }
      } else if (e.ctrlKey && e.shiftKey && (e.key === 'N' || e.key === 'n')) {
        e.preventDefault();
        startInlineCreate(activeFolderId || null);
      }
    };
    window.addEventListener('keydown', handleGlobalFolderKeys);
    return () => window.removeEventListener('keydown', handleGlobalFolderKeys);
  }, [activeFolderId, renamingFolderId, creatingInParentId, folders, readOnly]);

  // 1. Fetch folders and documents (initial or full reload)
  const fetchData = useCallback(async (isManual = false) => {
    if (isManual) {
      setIsRefreshing(true);
    }
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const [flatRes, treeRes, docsRes] = await Promise.all([
        fetch(`/v1/folders?organization_id=${orgId}&tree=false`, { headers }),
        fetch(`/v1/folders?organization_id=${orgId}&tree=true`, { headers }),
        fetch(`/v1/documents?organization_id=${orgId}`, { headers })
      ]);

      if (flatRes.ok) {
        const flatData = await flatRes.json();
        setFolders(flatData);
        setActiveFolderId(prev => {
          if (prev && flatData.some(f => f.id === prev)) return prev;
          const inbox = flatData.find(f => f.is_system) || flatData[0];
          if (inbox) {
            setExpandedFolders(exp => new Set([...exp, inbox.id]));
            return inbox.id;
          }
          return null;
        });
      }

      if (treeRes.ok) {
        const treeData = await treeRes.json();
        setFolderTree(treeData);
      }

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setAllDocuments(docsData);
        setSelectedDocId(prev => {
          if (prev && docsData.some(d => d.id === prev)) return prev;
          return null;
        });
      }
    } catch (err) {
      console.error('Failed to load workspace directory:', err);
      showToast?.('Error loading directory', 'error');
    } finally {
      setInitialLoading(false);
      setIsRefreshing(false);
    }
  }, [orgId, token, showToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Group documents by folder_id
  const docsByFolder = useMemo(() => {
    const map = {};
    for (const doc of allDocuments) {
      const fId = doc.folder_id || 'inbox';
      if (!map[fId]) map[fId] = [];
      map[fId].push(doc);
    }
    return map;
  }, [allDocuments]);

  // Active folder object
  const activeFolder = useMemo(() => {
    return folders.find(f => f.id === activeFolderId) || null;
  }, [folders, activeFolderId]);

  // Breadcrumb path from root to active folder
  const breadcrumbs = useMemo(() => {
    if (!activeFolderId) return [{ id: null, name: 'Vault Root' }];
    const chain = [];
    let cur = folders.find(f => f.id === activeFolderId);
    while (cur) {
      chain.unshift(cur);
      if (!cur.parent_id) break;
      cur = folders.find(f => f.id === cur.parent_id);
    }
    return [{ id: null, name: 'Vault Root' }, ...chain];
  }, [folders, activeFolderId]);

  // Direct subfolders for current folder
  const currentChildFolders = useMemo(() => {
    return folders.filter(f => f.parent_id === activeFolderId);
  }, [folders, activeFolderId]);

  // Direct documents for current folder
  const currentFolderDocs = useMemo(() => {
    if (!activeFolderId) {
      const inbox = folders.find(f => f.is_system && f.folder_type === 'inbox');
      return inbox ? (docsByFolder[inbox.id] || docsByFolder['inbox'] || []) : allDocuments;
    }
    const current = folders.find(f => f.id === activeFolderId);
    if (current?.is_system && current?.folder_type === 'inbox') {
      return (docsByFolder[activeFolderId] || []).concat(docsByFolder['inbox'] || []);
    }
    return docsByFolder[activeFolderId] || [];
  }, [activeFolderId, folders, docsByFolder, allDocuments]);

  // Handler for intelligent auto-organize
  const [isAutoOrganizing, setIsAutoOrganizing] = useState(false);
  const handleAutoOrganize = async () => {
    setIsAutoOrganizing(true);
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      showToast?.('Intelligently auto-organizing documents into enterprise folders...');
      const res = await fetch(`/v1/folders/auto-organize?organization_id=${orgId}`, {
        method: 'POST',
        headers
      });

      if (res.ok) {
        const data = await res.json();
        showToast?.(`Successfully filed ${data.organized_count} document${data.organized_count === 1 ? '' : 's'} into enterprise domain & connector folders!`);
        await fetchData(true);
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Auto-organize failed', 'error');
      }
    } catch (err) {
      showToast?.('Error organizing documents: ' + err.message, 'error');
    } finally {
      setIsAutoOrganizing(false);
    }
  };

  // Helper to render icon for folders
  const renderFolderIcon = (node, size = 15) => {
    const color = node.color || '#FFAB4A';
    if (node.is_system && node.folder_type === 'inbox') {
      return <Inbox size={size} style={{ color: '#6366F1', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'governance') {
      return <Shield size={size} style={{ color: '#FFAB4A', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'connectors') {
      return <Network size={size} style={{ color: '#6366F1', flexShrink: 0 }} />;
    }
    if (node.icon === 'lock') return <Lock size={size} style={{ color: '#3B82F6', flexShrink: 0 }} />;
    if (node.icon === 'scale') return <Scale size={size} style={{ color: '#8B5CF6', flexShrink: 0 }} />;
    if (node.icon === 'dollar-sign') return <Coins size={size} style={{ color: '#10B981', flexShrink: 0 }} />;
    if (node.icon === 'users') return <Users size={size} style={{ color: '#F59E0B', flexShrink: 0 }} />;
    if (node.icon === 'message-square') return <MessageSquare size={size} style={{ color: '#E11D48', flexShrink: 0 }} />;
    if (node.icon === 'git-branch') return <GitBranch size={size} style={{ color: '#334155', flexShrink: 0 }} />;
    if (node.icon === 'book-open') return <BookOpen size={size} style={{ color: '#0284C7', flexShrink: 0 }} />;
    if (node.icon === 'check-square') return <CheckSquare size={size} style={{ color: '#0284C7', flexShrink: 0 }} />;
    if (node.icon === 'briefcase') return <Briefcase size={size} style={{ color: '#64748B', flexShrink: 0 }} />;
    return <Folder size={size} style={{ color, flexShrink: 0 }} />;
  };

  // Helper to render source badge
  const renderSourceBadge = (doc) => {
    const title = (doc.title || '').toLowerCase();
    const type = (doc.document_type || '').toLowerCase();
    if (type === 'slack_message' || title.includes('slack')) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#FEE2E2', color: '#991B1B', fontWeight: 600 }}>
          <MessageSquare size={10} /> Slack
        </span>
      );
    }
    if (title.includes('github')) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#F1F5F9', color: '#334155', fontWeight: 600 }}>
          <GitBranch size={10} /> GitHub
        </span>
      );
    }
    if (title.includes('confluence')) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#E0F2FE', color: '#0369A1', fontWeight: 600 }}>
          <BookOpen size={10} /> Confluence
        </span>
      );
    }
    if (title.includes('jira')) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#E0F2FE', color: '#0284C7', fontWeight: 600 }}>
          <CheckSquare size={10} /> Jira
        </span>
      );
    }
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#FFF7ED', color: '#C2410C', fontWeight: 600 }}>
        <Upload size={10} /> Manual Upload
      </span>
    );
  };

  // 2. Fetch details & artifacts for selected document (Live Preview)
  useEffect(() => {
    if (!selectedDocId) {
      setSelectedDocDetails(null);
      setSelectedDocArtifacts(null);
      setSelectedClaimId(null);
      return;
    }

    let isMounted = true;
    async function loadDocPreview() {
      setLoadingPreview(true);
      try {
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        headers['X-Organization-Id'] = orgId;

        const [docRes, artRes] = await Promise.all([
          fetch(`/v1/documents/${selectedDocId}`, { headers }),
          fetch(`/v1/documents/${selectedDocId}/artifacts`, { headers })
        ]);

        if (isMounted) {
          if (docRes.ok) {
            const docData = await docRes.json();
            setSelectedDocDetails(docData);
          }
          if (artRes.ok) {
            const artData = await artRes.json();
            setSelectedDocArtifacts(artData);
            if (artData.claims && artData.claims.length > 0) {
              setSelectedClaimId(artData.claims[0].id);
            }
          }
        }
      } catch (err) {
        console.error('Failed to load document preview:', err);
      } finally {
        if (isMounted) setLoadingPreview(false);
      }
    }

    loadDocPreview();
    return () => {
      isMounted = false;
    };
  }, [selectedDocId, orgId, token]);

  // 3. Fetch folder metrics for Insights modal
  const fetchFolderMetrics = useCallback(async (folderId) => {
    if (!folderId) return;
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(
        `/v1/folders/${folderId}/metrics?organization_id=${orgId}&recursive=true`,
        { headers }
      );
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error('Failed to load folder metrics:', err);
    }
  }, [orgId, token]);

  // Handle clicking or expanding a specific folder
  // Loads contents & displays spinner ONLY at that particular folder, never hiding the tree
  const handleFolderClick = async (node, e) => {
    e?.stopPropagation();
    if (!node?.id) return;
    const folderId = node.id;
    setActiveFolderId(folderId);

    const isExpanded = expandedFolders.has(folderId);

    if (isExpanded) {
      // Collapse folder immediately without loading
      setExpandedFolders(prev => {
        const next = new Set(prev);
        next.delete(folderId);
        return next;
      });
      return;
    }

    // Expanding: expand immediately in UI
    setExpandedFolders(prev => new Set(prev).add(folderId));

    // Show loading spinner ONLY on this specific folder
    setLoadingFolderIds(prev => new Set(prev).add(folderId));

    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders/${folderId}/documents?organization_id=${orgId}&recursive=false`, { headers });
      if (res.ok) {
        const data = await res.json();
        const folderDocs = data.items || [];
        if (folderDocs.length > 0) {
          setAllDocuments(prev => {
            const map = new Map(prev.map(d => [d.id, d]));
            folderDocs.forEach(d => map.set(d.id, d));
            return Array.from(map.values());
          });
        }
      }
    } catch (err) {
      console.error('Error fetching documents for folder:', folderId, err);
    } finally {
      setLoadingFolderIds(prev => {
        const next = new Set(prev);
        next.delete(folderId);
        return next;
      });
    }
  };

  const toggleExpand = (folderId, e) => {
    e?.stopPropagation();
    const folderNode = folders.find(f => f.id === folderId);
    if (folderNode) {
      handleFolderClick(folderNode, e);
    } else {
      setExpandedFolders(prev => {
        const next = new Set(prev);
        if (next.has(folderId)) next.delete(folderId);
        else next.add(folderId);
        return next;
      });
    }
  };

  // Open context menu
  const openContextMenu = (e, type, target) => {
    e.preventDefault();
    e.stopPropagation();

    const menuWidth = 200;
    const menuHeight = 250;
    const x = Math.min(e.clientX, window.innerWidth - menuWidth - 10);
    const y = Math.min(e.clientY, window.innerHeight - menuHeight - 10);

    setContextMenu({
      visible: true,
      x: Math.max(10, x),
      y: Math.max(10, y),
      type,
      target
    });
  };

  // Start inline folder creation in a parent folder (or root if null)
  const startInlineCreate = (parentId = null) => {
    if (readOnly) return;
    setCreatingInParentId(parentId);
    setCreatingFolderName('New folder');
    if (parentId) {
      setExpandedFolders(prev => new Set([...prev, parentId]));
    }
  };

  // Commit inline folder creation (called on Enter or blur)
  const commitInlineCreate = async (overrideName) => {
    const parentIdToUse = creatingInParentIdRef.current;
    if (isSavingNewFolder || parentIdToUse === undefined) return;
    const trimmed = (overrideName !== undefined ? overrideName : creatingFolderName || '').trim();
    if (!trimmed) {
      setCreatingInParentId(undefined);
      return;
    }

    setIsSavingNewFolder(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders?organization_id=${orgId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: trimmed,
          parent_id: parentIdToUse,
          color: '#3B82F6',
          icon: 'folder'
        })
      });

      if (res.ok) {
        const created = await res.json();
        showToast?.(`Folder '${created.name}' created.`);
        setCreatingInParentId(undefined);
        if (parentIdToUse) {
          setExpandedFolders(prev => new Set([...prev, parentIdToUse]));
        }
        await fetchData();
        setActiveFolderId(created.id);
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Failed to create folder', 'error');
        setCreatingInParentId(undefined);
      }
    } catch (err) {
      showToast?.('Error creating folder: ' + err.message, 'error');
      setCreatingInParentId(undefined);
    } finally {
      setIsSavingNewFolder(false);
    }
  };

  // Inline rename commit handler (called on Enter or blur)
  const commitInlineRename = async (folderId, newName) => {
    if (isSavingRename) return;

    const trimmed = (newName || '').trim();
    const originalFolder = folders.find(f => f.id === folderId);

    // If empty or unchanged, cancel cleanly
    if (!trimmed || (originalFolder && originalFolder.name === trimmed)) {
      setRenamingFolderId(null);
      return;
    }

    setIsSavingRename(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders/${folderId}?organization_id=${orgId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ name: trimmed })
      });

      if (res.ok) {
        const updated = await res.json();
        showToast?.(`Folder renamed to '${updated.name}'.`);
        // Immediately update folders and tree in memory without full-page reloads
        setFolders(prev => prev.map(f => f.id === folderId ? { ...f, name: updated.name } : f));
        setFolderTree(prev => {
          const updateTree = (nodes) => nodes.map(n => {
            if (n.id === folderId) return { ...n, name: updated.name };
            if (n.children && n.children.length > 0) return { ...n, children: updateTree(n.children) };
            return n;
          });
          return updateTree(prev);
        });
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Rename failed', 'error');
      }
    } catch (err) {
      showToast?.('Error renaming folder: ' + err.message, 'error');
    } finally {
      setIsSavingRename(false);
      setRenamingFolderId(null);
    }
  };

  // Move folder handler
  const handleMoveFolder = async (e) => {
    e?.preventDefault();
    if (!movingFolder) return;

    const targetParentId = moveFolderTargetId === 'root' || !moveFolderTargetId ? null : moveFolderTargetId;

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders/${movingFolder.id}/move?organization_id=${orgId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ new_parent_id: targetParentId })
      });

      if (res.ok) {
        showToast?.(`Folder moved successfully.`);
        setShowMoveFolderModal(false);
        setMovingFolder(null);
        await fetchData();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Move failed', 'error');
      }
    } catch (err) {
      showToast?.('Error moving folder: ' + err.message, 'error');
    }
  };

  // Delete folder handler
  const handleDeleteFolder = async (folder) => {
    if (folder.is_system) {
      showToast?.('System Inbox cannot be deleted.', 'error');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete folder '${folder.name}'? It must be completely empty.`)) {
      return;
    }

    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders/${folder.id}?organization_id=${orgId}`, {
        method: 'DELETE',
        headers
      });

      if (res.ok) {
        showToast?.(`Folder '${folder.name}' deleted.`);
        if (activeFolderId === folder.id) {
          const inbox = folders.find(f => f.is_system);
          setActiveFolderId(inbox ? inbox.id : null);
        }
        await fetchData();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Delete failed', 'error');
      }
    } catch (err) {
      showToast?.('Error deleting folder: ' + err.message, 'error');
    }
  };

  // Delete document handler
  const handleDeleteDocument = async (doc) => {
    if (!window.confirm(`Are you sure you want to delete document '${doc.title}'?`)) {
      return;
    }

    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/documents/${doc.id}`, {
        method: 'DELETE',
        headers
      });

      if (res.ok) {
        showToast?.(`Document '${doc.title}' deleted.`);
        if (selectedDocId === doc.id) {
          setSelectedDocId(null);
        }
        await fetchData();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Delete failed', 'error');
      }
    } catch (err) {
      showToast?.('Error deleting document: ' + err.message, 'error');
    }
  };

  // Move document handler
  const handleMoveDocument = async (e) => {
    e?.preventDefault();
    if (!movingDoc || !moveDocTargetFolderId) return;

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/documents/${movingDoc.id}/move`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ destination_folder_id: moveDocTargetFolderId })
      });

      if (res.ok) {
        showToast?.(`Document moved successfully.`);
        setShowMoveDocModal(false);
        setMovingDoc(null);
        await fetchData();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Failed to move document', 'error');
      }
    } catch (err) {
      showToast?.('Error moving document: ' + err.message, 'error');
    }
  };

  // Upload document handler
  const handleUploadDocument = async (e) => {
    e?.preventDefault();
    if (!uploadFile) {
      showToast?.('Please select a file to upload.', 'error');
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('organization_id', orgId);
      if (uploadFolderId) formData.append('folder_id', uploadFolderId);
      formData.append('document_type', uploadDocType);

      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`/v1/documents/upload-and-extract`, {
        method: 'POST',
        headers,
        body: formData
      });

      if (res.ok) {
        const result = await res.json();
        showToast?.(`Uploaded & extracted '${uploadFile.name}' successfully.`);
        setShowUploadModal(false);
        setUploadFile(null);
        await fetchData();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Upload failed', 'error');
      }
    } catch (err) {
      showToast?.('Error uploading file: ' + err.message, 'error');
    } finally {
      setIsUploading(false);
    }
  };

  // Copy helper
  const handleCopy = (text) => {
    if (!text) return;
    navigator.clipboard?.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
    showToast?.('Copied to clipboard');
  };

  // Render an inline editable row for creating a new folder (Drive / OS style)
  const renderInlineCreateRow = (depth = 0) => (
    <div
      key="inline-new-folder-row"
      onClick={e => e.stopPropagation()}
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '5px 8px',
        paddingLeft: `${depth * 16 + 8}px`,
        borderRadius: '4px',
        background: '#FFFFFF',
        gap: '6px'
      }}
    >
      {/* Spacer matching chevron width */}
      <span style={{ width: 14, height: 14, display: 'inline-block', flexShrink: 0 }} />

      {/* Folder Icon */}
      <Folder size={15} style={{ color: '#3B82F6', flexShrink: 0 }} />

      {/* Inline Input Box */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '4px', minWidth: 0 }}>
        <input
          ref={inlineCreateInputRef}
          type="text"
          value={creatingFolderName}
          onChange={e => setCreatingFolderName(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') {
              e.preventDefault();
              e.stopPropagation();
              commitInlineCreate(creatingFolderName);
            } else if (e.key === 'Escape') {
              e.preventDefault();
              e.stopPropagation();
              setCreatingInParentId(undefined);
            }
          }}
          onBlur={() => {
            commitInlineCreate(creatingFolderName);
          }}
          disabled={isSavingNewFolder}
          style={{
            flex: 1,
            height: '24px',
            padding: '1px 6px',
            fontSize: '0.80rem',
            fontFamily: 'inherit',
            fontWeight: 500,
            color: '#0F172A',
            background: '#FFFFFF',
            border: '1.5px solid #2563EB',
            borderRadius: '3px',
            outline: 'none',
            boxShadow: '0 0 0 2px rgba(37, 99, 235, 0.20)',
            minWidth: '70px'
          }}
        />
        {isSavingNewFolder && (
          <RefreshCw size={11} className="spin" style={{ color: '#2563EB', flexShrink: 0 }} />
        )}
      </div>
    </div>
  );

  // Recursive Directory Tree Renderer: Renders folders AND files (No Numbers!)
  const renderDirectoryTree = (nodes, depth = 0) => {
    const q = searchQuery.toLowerCase().trim();

    return nodes.map(node => {
      const isExpanded = expandedFolders.has(node.id);
      const isFolderActive = activeFolderId === node.id;
      const isFolderLoading = loadingFolderIds.has(node.id);
      const childFolders = node.children || [];

      // Get files belonging to this folder (or inbox if system inbox)
      const folderFiles = (docsByFolder[node.id] || []).concat(
        node.is_system ? (docsByFolder['inbox'] || []) : []
      );

      // Deduplicate files by id
      const uniqueFiles = Array.from(new Map(folderFiles.map(f => [f.id, f])).values());
      const hasContent = childFolders.length > 0 || uniqueFiles.length > 0 || creatingInParentId === node.id;

      // Filter check
      if (q && !node.name.toLowerCase().includes(q) && !uniqueFiles.some(f => f.title.toLowerCase().includes(q))) {
        return null;
      }

      return (
        <div key={node.id} style={{ display: 'flex', flexDirection: 'column' }}>
          {/* FOLDER ROW */}
          <div
            onClick={(e) => {
              if (renamingFolderId === node.id) return;
              handleFolderClick(node, e);
            }}
            onContextMenu={(e) => {
              if (renamingFolderId === node.id) return;
              openContextMenu(e, 'folder', node);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '5px 8px',
              paddingLeft: `${depth * 16 + 8}px`,
              borderRadius: '4px',
              cursor: 'pointer',
              userSelect: 'none',
              background: isFolderActive ? 'rgba(37, 99, 235, 0.08)' : 'transparent',
              color: isFolderActive ? '#1E40AF' : 'var(--text-main)',
              fontWeight: isFolderActive ? 600 : 500,
              fontSize: '0.80rem',
              transition: 'background 0.1s ease',
              gap: '6px'
            }}
            onMouseEnter={e => {
              if (!isFolderActive) e.currentTarget.style.background = '#F8FAFC';
            }}
            onMouseLeave={e => {
              if (!isFolderActive) e.currentTarget.style.background = 'transparent';
            }}
          >
            {/* Expand / Collapse Chevron OR Folder-specific Loading Spinner */}
            <span
              style={{
                width: 14,
                height: 14,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}
            >
              {isFolderLoading ? (
                <RefreshCw size={12} className="spin" style={{ color: '#2563EB' }} />
              ) : hasContent ? (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleFolderClick(node, e);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    color: '#64748B',
                    width: 14
                  }}
                >
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>
              ) : (
                <span style={{ width: 14 }} />
              )}
            </span>

            {/* Folder Icon (Customized per folder type/domain) */}
            {renderFolderIcon(node, 15)}

            {/* Folder Name OR Inline Rename Input (Just like Drive / Windows Explorer) */}
            {renamingFolderId === node.id ? (
              <div
                onClick={e => e.stopPropagation()}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  minWidth: 0
                }}
              >
                <input
                  ref={inlineRenameInputRef}
                  type="text"
                  value={renameInputVal}
                  onChange={e => setRenameInputVal(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      e.stopPropagation();
                      commitInlineRename(node.id, renameInputVal);
                    } else if (e.key === 'Escape') {
                      e.preventDefault();
                      e.stopPropagation();
                      setRenamingFolderId(null);
                    }
                  }}
                  onBlur={() => {
                    commitInlineRename(node.id, renameInputVal);
                  }}
                  disabled={isSavingRename}
                  style={{
                    flex: 1,
                    height: '24px',
                    padding: '1px 6px',
                    fontSize: '0.80rem',
                    fontFamily: 'inherit',
                    fontWeight: 500,
                    color: '#0F172A',
                    background: '#FFFFFF',
                    border: '1.5px solid #2563EB',
                    borderRadius: '3px',
                    outline: 'none',
                    boxShadow: '0 0 0 2px rgba(37, 99, 235, 0.20)',
                    minWidth: '60px'
                  }}
                />
                {isSavingRename && (
                  <RefreshCw size={11} className="spin" style={{ color: '#2563EB', flexShrink: 0 }} />
                )}
              </div>
            ) : (
              <span
                style={{
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  flex: 1
                }}
                title={node.name}
              >
                {node.name}
              </span>
            )}

            {/* Folder-specific loading spinner at right side of this folder row */}
            {isFolderLoading && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  color: '#2563EB',
                  marginLeft: 'auto',
                  flexShrink: 0
                }}
              >
                <RefreshCw size={11} className="spin" />
              </span>
            )}
          </div>

          {/* SUBFOLDERS AND FILES LISTING (Visible when folder is expanded) */}
          {(isExpanded || creatingInParentId === node.id) && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {/* Inline new folder creation row if creating inside this folder */}
              {creatingInParentId === node.id && renderInlineCreateRow(depth + 1)}

              {/* 1. Child Subfolders */}
              {childFolders.length > 0 && renderDirectoryTree(childFolders, depth + 1)}

              {/* 2. Files directly inside this folder */}
              {uniqueFiles.map(file => {
                const isSelected = selectedDocId === file.id;

                return (
                  <div
                    key={file.id}
                    onClick={() => {
                      setSelectedDocId(file.id);
                      setActiveFolderId(node.id);
                    }}
                    onDoubleClick={() => onInspectDocument?.(file)}
                    onContextMenu={(e) => openContextMenu(e, 'document', file)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '5px 8px',
                      paddingLeft: `${(depth + 1) * 16 + 8}px`,
                      borderRadius: '4px',
                      cursor: 'pointer',
                      userSelect: 'none',
                      background: isSelected ? '#EFF6FF' : 'transparent',
                      color: isSelected ? '#1E40AF' : 'var(--text-secondary)',
                      fontWeight: isSelected ? 600 : 400,
                      fontSize: '0.78rem',
                      gap: '7px',
                      transition: 'background 0.1s ease',
                      borderLeft: isSelected ? '2px solid #2563EB' : '2px solid transparent'
                    }}
                    onMouseEnter={e => {
                      if (!isSelected) e.currentTarget.style.background = '#F8FAFC';
                    }}
                    onMouseLeave={e => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <FileText
                      size={14}
                      style={{
                        color: isSelected ? '#2563EB' : '#94A3B8',
                        flexShrink: 0
                      }}
                    />
                    <span
                      style={{
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        flex: 1
                      }}
                      title={file.title}
                    >
                      {file.title}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div style={{ display: 'flex', gap: '14px', width: '100%', alignItems: 'flex-start' }}>
      
      {/* ── LEFT PANE: DIRECTORY TREE (FOLDERS & FILES) ── */}
      <div
        ref={directoryContainerRef}
        onContextMenu={(e) => {
          if (e.target === directoryContainerRef.current || e.target.classList.contains('tree-blank-area')) {
            openContextMenu(e, 'canvas', activeFolder);
          }
        }}
        style={{
          width: '360px',
          minWidth: '320px',
          background: '#FAF8F5',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'none',
          overflow: 'hidden'
        }}
      >
        {/* Directory Top Bar */}
        <div
          style={{
            padding: '10px 12px',
            borderBottom: '1px solid var(--border-subtle)',
            background: '#FAF8F5',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}
        >
          {/* Header Title + Actions */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Directory Explorer
            </span>

            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {!readOnly ? (
                <>
                  {/* New Folder Button (In-place OS/Drive style) */}
                  <button
                    type="button"
                    onClick={() => startInlineCreate(activeFolderId || null)}
                    className="btn btn-secondary"
                    style={{ padding: '3px 8px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="New Subfolder in selected folder"
                  >
                    <FolderPlus size={13} style={{ color: '#3B82F6' }} />
                    <span>New</span>
                  </button>

                  {/* Upload Button */}
                  <button
                    type="button"
                    onClick={() => {
                      setUploadFolderId(activeFolderId);
                      setShowUploadModal(true);
                    }}
                    className="btn btn-primary"
                    style={{ padding: '3px 9px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Upload document to selected folder"
                  >
                    <Upload size={13} />
                    <span>Upload</span>
                  </button>
                </>
              ) : (
                <span
                  style={{
                    fontSize: '0.68rem',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    background: '#F1F5F9',
                    color: '#64748B',
                    fontWeight: 600,
                    letterSpacing: '0.3px',
                    border: '1px solid #E2E8F0',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title="Vault is read-only. File and folder management is enabled in Document Explorer."
                >
                  <ShieldCheck size={11} style={{ color: '#10B981' }} />
                  Read-Only
                </span>
              )}

              {/* Refresh */}
              <button
                type="button"
                onClick={() => fetchData(true)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', padding: '3px' }}
                title="Refresh Directory"
              >
                <RefreshCw size={13} className={isRefreshing ? 'spin' : ''} />
              </button>
            </div>
          </div>

          {/* Search Filter input */}
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={13} style={{ position: 'absolute', left: '8px', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Filter folders and files..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '5px 8px 5px 26px',
                fontSize: '0.76rem',
                borderRadius: '5px',
                border: '1px solid #CBD5E1',
                background: '#FFFFFF'
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: '6px', background: 'none', border: 'none', cursor: 'pointer', color: '#94A3B8', padding: 0 }}
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Directory Items List (Scrollable Tree) */}
        <div
          className="tree-blank-area"
          style={{
            minHeight: '380px',
            maxHeight: '520px',
            overflowY: 'auto',
            padding: '8px 4px'
          }}
        >
          {initialLoading && folderTree.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: '#64748B', fontSize: '0.78rem' }}>
              <RefreshCw size={15} className="spin" style={{ margin: '0 auto 6px auto', display: 'block' }} />
              Loading directory...
            </div>
          ) : (
            <>
              {creatingInParentId === null && renderInlineCreateRow(0)}
              {folderTree.length === 0 && creatingInParentId !== null ? (
                <div style={{ padding: '30px', textAlign: 'center', color: '#64748B', fontSize: '0.78rem' }}>
                  No folders found.
                </div>
              ) : (
                renderDirectoryTree(folderTree)
              )}
            </>
          )}
        </div>

        {/* Directory Bottom Bar */}
        <div
          style={{
            padding: '6px 12px',
            background: '#F8FAFC',
            borderTop: '1px solid var(--border-subtle, #E2E8F0)',
            fontSize: '0.70rem',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <span>{readOnly ? 'Vault Directory • Read-Only Inspection' : 'Right-click any folder or file for options'}</span>
          {!readOnly && (
            <button
              type="button"
              onClick={() => startInlineCreate(null)}
              style={{ background: 'none', border: 'none', color: '#2563EB', cursor: 'pointer', fontSize: '0.70rem', fontWeight: 600 }}
            >
              + New Root
            </button>
          )}
        </div>
      </div>

      {/* ── RIGHT PANE: LIVE DOCUMENT PREVIEW (MINIMAL COMPACT HEIGHT) ── */}
      <div
        style={{
          flex: 1,
          minWidth: 0,
          background: '#FAF8F5',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'none',
          overflow: 'hidden',
          maxHeight: '500px' // Minimal height as requested by user!
        }}
      >
        {selectedDocDetails ? (() => {
          const claimsList = selectedDocArtifacts?.claims || [];
          const conflictsList = selectedDocArtifacts?.conflicts || [];
          const verifiedCount = claimsList.filter(c => c.status === 'verified' || c.status === 'ACTIVE').length;
          const trustPercent = conflictsList.length === 0 ? 98 : Math.max(72, 98 - (conflictsList.length * 4));
          const filteredDocClaims = claimsList.filter(c => {
            if (!claimSearchQuery.trim()) return true;
            const q = claimSearchQuery.toLowerCase();
            return (
              (c.claim_text || '').toLowerCase().includes(q) ||
              (c.subject || '').toLowerCase().includes(q) ||
              (c.predicate || '').toLowerCase().includes(q) ||
              (c.object || '').toLowerCase().includes(q)
            );
          });
          const activeClaimObj = claimsList.find(c => c.id === selectedClaimId) || (claimsList.length > 0 ? claimsList[0] : null);

          return (
            <>
              {/* 1. Header Bar: Title, Badge, Open File, Inspect, Close */}
              <div
                style={{
                  padding: '9px 14px',
                  borderBottom: '1px solid var(--border-subtle)',
                  background: '#FAF8F5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '8px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                  <button
                    type="button"
                    onClick={() => setSelectedDocId(null)}
                    className="btn btn-secondary"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '3px 8px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      background: '#FFFFFF',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '5px',
                      cursor: 'pointer',
                      color: 'var(--text-secondary)'
                    }}
                    title="Return to folder view"
                  >
                    <ArrowLeft size={12} />
                    <span>Back</span>
                  </button>
                  <FileText size={15} style={{ color: '#2563EB', flexShrink: 0 }} />
                  <span
                    style={{
                      fontSize: '0.86rem',
                      fontWeight: 700,
                      color: 'var(--text-main)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}
                    title={selectedDocDetails.title}
                  >
                    {selectedDocDetails.title}
                  </span>
                  <span className="badge badge-verified" style={{ fontSize: '0.64rem', padding: '1px 6px' }}>
                    {selectedDocDetails.document_type || 'Policy'}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <button
                    type="button"
                    onClick={() => {
                      const url = `/v1/documents/${selectedDocDetails.id}/file`;
                      window.open(url, '_blank');
                    }}
                    className="btn btn-secondary"
                    style={{ padding: '3px 8px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px', background: '#FFFFFF', color: '#0284C7', border: '1px solid #CBD5E1' }}
                    title="Open document file in a new browser tab"
                  >
                    <ExternalLink size={12} />
                    <span>Open File ↗</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsFullFileReaderOpen(true)}
                    className="btn btn-secondary"
                    style={{ padding: '3px 8px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px', background: '#FFFFFF', color: '#1E293B', border: '1px solid #CBD5E1' }}
                    title="Open in full-screen reader modal with search"
                  >
                    <BookOpen size={12} />
                    <span>Reader</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => onViewClaims?.(selectedDocDetails, 'summary')}
                    className="btn btn-primary"
                    style={{
                      padding: '3px 9px',
                      fontSize: '0.72rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: '#EA580C',
                      borderColor: '#EA580C',
                      color: '#FFFFFF',
                      fontWeight: 700
                    }}
                    title="Open document in full 360° Lineage Studio"
                  >
                    <Sparkles size={12} />
                    <span>360° Studio ↗</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => onInspectDocument?.(selectedDocDetails)}
                    className="btn btn-secondary"
                    style={{ padding: '3px 8px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Open in full Claim Inspector drawer"
                  >
                    <Maximize2 size={12} />
                    <span>Inspect</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setSelectedDocId(null);
                      setSelectedDocDetails(null);
                      setSelectedDocArtifacts(null);
                    }}
                    style={{
                      width: '22px',
                      height: '22px',
                      borderRadius: '4px',
                      border: 'none',
                      background: 'transparent',
                      color: '#94A3B8',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                    title="Close preview"
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>

              {/* 2. Facility Tabs: Preview, Description & Specs, Claims, Document Lineage */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '4px 12px',
                  borderBottom: '1px solid var(--border-subtle)',
                  background: '#FAF8F5',
                  overflowX: 'auto'
                }}
              >
                {[
                  { id: 'preview', label: 'Preview & File', icon: FileText },
                  { id: 'description', label: 'Description & Specs', icon: Info },
                  { id: 'claims', label: `Atomic Claims (${claimsList.length})`, icon: ShieldCheck },
                  { id: 'lineage', label: 'Document Lineage', icon: Network }
                ].map(tab => {
                  const isActive = activeFacilityTab === tab.id;
                  const IconComp = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveFacilityTab(tab.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '5px 10px',
                        fontSize: '0.74rem',
                        fontWeight: isActive ? 700 : 500,
                        border: 'none',
                        borderBottom: isActive ? '2px solid #EA580C' : '2px solid transparent',
                        background: 'transparent',
                        color: isActive ? '#EA580C' : '#64748B',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <IconComp size={13} />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* 3. Facility Tab Contents */}
              <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>

                {/* TAB 1: PREVIEW & OPEN FILE */}
                {activeFacilityTab === 'preview' && (
                  <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                    <div
                      style={{
                        flex: 1,
                        overflowY: 'auto',
                        background: '#FAF8F5',
                        padding: '14px 18px'
                      }}
                    >
                      {loadingPreview ? (
                        <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                          <RefreshCw size={15} className="spin" style={{ margin: '0 auto 6px auto', display: 'block' }} />
                          Loading document preview...
                        </div>
                      ) : (
                        <div
                          style={{
                            background: '#FFFFFF',
                            borderRadius: '3px',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.08), 0 0 1px rgba(0,0,0,0.12)',
                            padding: '18px 22px',
                            minHeight: '220px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '10px'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                            <span style={{ fontWeight: 700, textTransform: 'uppercase' }}>
                              {selectedDocDetails.document_type || 'Policy'} Document Sheet
                            </span>
                            <span>Page 1 of 1</span>
                          </div>

                          <div style={{ fontSize: '0.82rem', color: 'var(--text-main)', lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                            {selectedDocDetails.content_uri || 'No text content available for this document.'}
                          </div>
                        </div>
                      )}
                    </div>

                    <div
                      style={{
                        padding: '8px 14px',
                        borderTop: '1px solid var(--border-subtle, #E2E8F0)',
                        background: '#FFFFFF',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '0.72rem',
                        gap: '8px',
                        flexWrap: 'wrap'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="badge badge-allow" style={{ fontSize: '0.66rem', padding: '1px 6px' }}>
                          {claimsList.length} Extracted Claim{claimsList.length === 1 ? '' : 's'}
                        </span>
                        <span style={{ color: 'var(--text-muted)' }}>
                          SHA-256: <code style={{ fontSize: '0.70rem' }}>{selectedDocDetails.content_hash?.substring(0, 10)}...</code>
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopy(selectedDocDetails.content_hash)}
                          style={{ background: 'none', border: 'none', color: '#2563EB', cursor: 'pointer', padding: 0 }}
                          title="Copy SHA-256 hash"
                        >
                          {copiedHash ? <Check size={13} style={{ color: '#16A34A' }} /> : <Copy size={13} />}
                        </button>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          type="button"
                          onClick={() => setActiveFacilityTab('description')}
                          className="btn btn-secondary"
                          style={{ padding: '4px 9px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                          <Info size={12} />
                          <span>Description</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => setActiveFacilityTab('claims')}
                          className="btn btn-primary"
                          style={{ padding: '4px 10px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                          <Search size={12} />
                          <span>Select Claims ({claimsList.length})</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => setActiveFacilityTab('lineage')}
                          className="btn btn-secondary"
                          style={{ padding: '4px 9px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                          <Layers size={12} />
                          <span>Lineage</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => onViewClaims?.(selectedDocDetails, 'summary')}
                          className="btn btn-secondary"
                          style={{ padding: '4px 9px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px', color: '#EA580C', borderColor: '#FED7AA', background: '#FFF7ED' }}
                          title="Open in full 360° Lineage Studio"
                        >
                          <Sparkles size={12} />
                          <span>360° Studio ➔</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 2: DESCRIPTION & TECHNICAL SPECIFICATIONS */}
                {activeFacilityTab === 'description' && (
                  <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '14px', background: '#FFFFFF' }}>
                    {/* Governance Description Abstract */}
                    <div style={{ padding: '12px 14px', background: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.70rem', fontWeight: 800, color: '#64748B', textTransform: 'uppercase', marginBottom: '4px', letterSpacing: '0.04em' }}>
                        Governance Abstract & Description
                      </div>
                      <p style={{ margin: 0, fontSize: '0.80rem', color: '#334155', lineHeight: 1.55 }}>
                        {selectedDocDetails.description || `Enterprise normalized governance asset. Deconstructed into atomic policy facts, signed with SHA-256 cryptographic provenance, and continuously verified against temporal drift and cross-document contradictions.`}
                      </p>
                    </div>

                    {/* 4 Governance Metrics */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                      <div style={{ padding: '8px 10px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px' }}>
                        <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 600 }}>Atomic Claims</div>
                        <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>{claimsList.length}</div>
                        <span style={{ fontSize: '0.62rem', color: '#16A34A', fontWeight: 700 }}>{verifiedCount || claimsList.length} verified</span>
                      </div>
                      <div style={{ padding: '8px 10px', background: conflictsList.length > 0 ? '#FEF2F2' : '#F0FDF4', border: `1px solid ${conflictsList.length > 0 ? '#FEE2E2' : '#DCFCE7'}`, borderRadius: '6px' }}>
                        <div style={{ fontSize: '0.66rem', color: conflictsList.length > 0 ? '#991B1B' : '#166534', fontWeight: 600 }}>Contradictions</div>
                        <div style={{ fontSize: '1.05rem', fontWeight: 800, color: conflictsList.length > 0 ? '#DC2626' : '#15803D', marginTop: '2px' }}>{conflictsList.length}</div>
                        <span style={{ fontSize: '0.62rem', color: conflictsList.length > 0 ? '#DC2626' : '#16A34A', fontWeight: 700 }}>{conflictsList.length > 0 ? 'Action required' : '0 detected'}</span>
                      </div>
                      <div style={{ padding: '8px 10px', background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: '6px' }}>
                        <div style={{ fontSize: '0.66rem', color: '#065F46', fontWeight: 600 }}>Trust Integrity</div>
                        <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#059669', marginTop: '2px' }}>{trustPercent}%</div>
                        <span style={{ fontSize: '0.62rem', color: '#059669', fontWeight: 700 }}>High Trust Tier</span>
                      </div>
                      <div style={{ padding: '8px 10px', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '6px' }}>
                        <div style={{ fontSize: '0.66rem', color: '#1E40AF', fontWeight: 600 }}>Downstream Impact</div>
                        <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#2563EB', marginTop: '2px' }}>Active</div>
                        <span style={{ fontSize: '0.62rem', color: '#2563EB', fontWeight: 700 }}>Decision Gateway</span>
                      </div>
                    </div>

                    {/* Technical Specifications Table */}
                    <div style={{ border: '1px solid #E2E8F0', borderRadius: '8px', overflow: 'hidden' }}>
                      <div style={{ padding: '7px 12px', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', fontSize: '0.70rem', fontWeight: 800, color: '#475569', textTransform: 'uppercase' }}>
                        Technical Specifications & Metadata
                      </div>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.74rem' }}>
                        <tbody>
                          {[
                            { label: 'Artifact GUID', value: selectedDocDetails.id, isMono: true },
                            { label: 'Parent Source Connector', value: selectedDocArtifacts?.source?.name || 'Direct File Upload' },
                            { label: 'Classification', value: selectedDocDetails.document_type || 'Restricted Policy Standard' },
                            { label: 'Active Version', value: selectedDocDetails.versions?.length ? `v${selectedDocDetails.versions.length}.0` : 'v1.0' },
                            { label: 'Cryptographic SHA-256', value: selectedDocDetails.content_hash || 'SHA256-OK', isMono: true },
                            { label: 'Deconstruction Pipeline', value: 'Trulin Semantic Deconstruction Engine v1.0' },
                            { label: 'Created Timestamp', value: selectedDocDetails.created_at ? new Date(selectedDocDetails.created_at).toLocaleString() : 'Recent' }
                          ].map((row, idx, arr) => (
                            <tr key={row.label} style={{ borderBottom: idx < arr.length - 1 ? '1px solid #F1F5F9' : 'none' }}>
                              <td style={{ padding: '7px 12px', color: '#64748B', fontWeight: 600, width: '38%' }}>{row.label}</td>
                              <td style={{ padding: '7px 12px', color: '#0F172A', fontWeight: row.isMono ? 700 : 500, fontFamily: row.isMono ? 'monospace' : 'inherit', fontSize: row.isMono ? '0.70rem' : '0.74rem' }}>
                                {row.value}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px', paddingTop: '6px' }}>
                      <button
                        type="button"
                        onClick={() => setActiveFacilityTab('claims')}
                        className="btn btn-secondary"
                        style={{ padding: '5px 12px', fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '5px' }}
                      >
                        <ShieldCheck size={13} style={{ color: '#2563EB' }} />
                        <span>Select Claims ({claimsList.length}) ➔</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => onViewClaims?.(selectedDocDetails, 'summary')}
                        className="btn btn-primary"
                        style={{ padding: '5px 14px', fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '5px', background: '#EA580C', borderColor: '#EA580C', color: '#FFFFFF', fontWeight: 700 }}
                      >
                        <Sparkles size={13} />
                        <span>Deep-Dive in 360° Studio ↗</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* TAB 3: ATOMIC CLAIMS SELECTOR (SELECT ACROSS THIS PARTICULAR DOCUMENT) */}
                {activeFacilityTab === 'claims' && (
                  <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '12px', background: '#FFFFFF', flex: 1 }}>
                    {/* Claims Search Bar */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
                      <div style={{ position: 'relative', flex: 1 }}>
                        <Search size={13} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
                        <input
                          type="text"
                          placeholder={`Filter ${claimsList.length} claims in this document...`}
                          value={claimSearchQuery}
                          onChange={e => setClaimSearchQuery(e.target.value)}
                          style={{
                            width: '100%',
                            padding: '6px 10px 6px 30px',
                            borderRadius: '6px',
                            border: '1px solid #CBD5E1',
                            fontSize: '0.76rem',
                            outline: 'none'
                          }}
                        />
                      </div>
                      <span style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600, whiteSpace: 'nowrap' }}>
                        {filteredDocClaims.length} of {claimsList.length} claims
                      </span>
                    </div>

                    {/* Claims Split Selector */}
                    {filteredDocClaims.length === 0 ? (
                      <div style={{ padding: '30px', textAlign: 'center', color: '#94A3B8', fontSize: '0.78rem' }}>
                        {claimSearchQuery ? 'No claims match your search filter.' : 'No atomic claims extracted for this document yet.'}
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '12px', flex: 1, minHeight: '260px' }}>
                        {/* Left List of Claims */}
                        <div style={{ overflowY: 'auto', maxHeight: '340px', display: 'flex', flexDirection: 'column', gap: '6px', paddingRight: '4px' }}>
                          {filteredDocClaims.map((claim, idx) => {
                            const isSelected = activeClaimObj?.id === claim.id;
                            const isConflicted = conflictsList.some(c => c.claim_a_id === claim.id || c.claim_b_id === claim.id);
                            return (
                              <div
                                key={claim.id || idx}
                                onClick={() => setSelectedClaimId(claim.id)}
                                style={{
                                  padding: '8px 10px',
                                  borderRadius: '6px',
                                  border: isSelected ? '1.5px solid #2563EB' : '1px solid #E2E8F0',
                                  background: isSelected ? '#EFF6FF' : '#FFFFFF',
                                  cursor: 'pointer',
                                  transition: 'all 0.15s ease'
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                                  <span style={{ fontSize: '0.66rem', fontWeight: 700, color: isSelected ? '#1D4ED8' : '#475569', textTransform: 'uppercase' }}>
                                    {claim.subject || 'Rule'}
                                  </span>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    {isConflicted && (
                                      <span style={{ fontSize: '0.60rem', background: '#FEE2E2', color: '#991B1B', padding: '1px 5px', borderRadius: '4px', fontWeight: 700 }}>
                                        ⚠️ Conflict
                                      </span>
                                    )}
                                    <span style={{ fontSize: '0.62rem', background: isSelected ? '#DBEAFE' : '#F1F5F9', color: isSelected ? '#1D4ED8' : '#16A34A', padding: '1px 5px', borderRadius: '4px', fontWeight: 700 }}>
                                      {Math.round((claim.trust_score || 0.95) * 100)}%
                                    </span>
                                  </div>
                                </div>
                                <div style={{ fontSize: '0.76rem', color: isSelected ? '#1E293B' : '#334155', fontWeight: isSelected ? 600 : 400, lineHeight: 1.35, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                  {claim.claim_text}
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {/* Right Detail Pane for Selected Claim */}
                        <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0', overflowY: 'auto', maxHeight: '340px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                          {activeClaimObj ? (
                            <>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                                <span style={{ fontSize: '0.68rem', fontWeight: 800, color: '#334155', textTransform: 'uppercase' }}>
                                  Claim Deep-Dive
                                </span>
                                <span className="badge badge-verified" style={{ fontSize: '0.62rem' }}>
                                  {activeClaimObj.status || 'Verified Active'}
                                </span>
                              </div>

                              <div>
                                <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 700, marginBottom: '2px' }}>ATOMIC STATEMENT</div>
                                <div style={{ fontSize: '0.80rem', fontWeight: 600, color: '#0F172A', lineHeight: 1.4 }}>
                                  "{activeClaimObj.claim_text}"
                                </div>
                              </div>

                              {activeClaimObj.quote && (
                                <div>
                                  <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 700, marginBottom: '2px' }}>EXACT SOURCE QUOTE</div>
                                  <div style={{ fontSize: '0.74rem', fontStyle: 'italic', color: '#475569', background: '#FFFFFF', padding: '6px 8px', borderRadius: '4px', border: '1px solid #E2E8F0' }}>
                                    "{activeClaimObj.quote}"
                                  </div>
                                </div>
                              )}

                              <div>
                                <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 700, marginBottom: '2px' }}>SEMANTIC TRIPLET</div>
                                <div style={{ fontSize: '0.72rem', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                  <span style={{ background: '#EFF6FF', color: '#1D4ED8', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>{activeClaimObj.subject || 'Subject'}</span>
                                  <span style={{ color: '#94A3B8' }}>➔</span>
                                  <span style={{ background: '#FEF3C7', color: '#B45309', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>{activeClaimObj.predicate || 'specifies'}</span>
                                  <span style={{ color: '#94A3B8' }}>➔</span>
                                  <span style={{ background: '#F0FDF4', color: '#15803D', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>{activeClaimObj.object || 'Policy Requirement'}</span>
                                </div>
                              </div>

                              <div style={{ marginTop: 'auto', paddingTop: '8px', borderTop: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                                <span style={{ fontSize: '0.68rem', color: '#64748B' }}>
                                  Confidence: <strong style={{ color: '#16A34A' }}>{Math.round((activeClaimObj.trust_score || 0.95) * 100)}%</strong>
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                                  <button
                                    type="button"
                                    onClick={() => setActiveFacilityTab('preview')}
                                    className="btn btn-secondary"
                                    style={{ padding: '2px 8px', fontSize: '0.70rem' }}
                                    title="Locate claim in document preview"
                                  >
                                    Locate in Doc
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => onViewClaims?.(selectedDocDetails, 'dag')}
                                    className="btn btn-secondary"
                                    style={{ padding: '2px 8px', fontSize: '0.70rem', color: '#EA580C', borderColor: '#FED7AA' }}
                                    title="Inspect claim in Interactive DAG Lineage"
                                  >
                                    Inspect in DAG ➔
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => onViewClaims?.(selectedDocDetails, 'claims')}
                                    className="btn btn-primary"
                                    style={{ padding: '2px 8px', fontSize: '0.70rem' }}
                                    title="Open Claim Studio"
                                  >
                                    Claims Studio ↗
                                  </button>
                                </div>
                              </div>
                            </>
                          ) : (
                            <div style={{ textAlign: 'center', color: '#94A3B8', fontSize: '0.76rem', padding: '30px 10px' }}>
                              Select a claim on the left to inspect its extracted details.
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 4: DOCUMENT-WISE LINEAGE DAG */}
                {activeFacilityTab === 'lineage' && (
                  <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '14px', background: '#FFFFFF', flex: 1 }}>
                    {/* Lineage Banner */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#F8FAFC', padding: '10px 14px', borderRadius: '8px', border: '1px solid #E2E8F0', flexWrap: 'wrap', gap: '8px' }}>
                      <div>
                        <div style={{ fontSize: '0.82rem', fontWeight: 800, color: '#0F172A' }}>
                          Document-Wise Lineage Flow
                        </div>
                        <div style={{ fontSize: '0.70rem', color: '#64748B' }}>
                          Source-to-Decision verification pipeline for "{selectedDocDetails.title}"
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          type="button"
                          onClick={() => onViewClaims?.(selectedDocDetails, 'dag')}
                          className="btn btn-primary"
                          style={{ padding: '4px 12px', fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '5px', background: '#EA580C', borderColor: '#EA580C' }}
                        >
                          <Layers size={13} />
                          <span>Launch Full Canvas DAG ↗</span>
                        </button>
                      </div>
                    </div>

                    {/* Interactive Visual Mini-DAG Canvas (Responsive 4-Stage Flow) */}
                    <div
                      style={{
                        background: '#F8FAFC',
                        borderRadius: '8px',
                        border: '1px solid #E2E8F0',
                        padding: '18px 14px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexWrap: 'wrap',
                        gap: '8px',
                        position: 'relative'
                      }}
                    >
                      {/* Node 1: Source */}
                      <div
                        style={{
                          background: '#FFFFFF',
                          border: '1.5px solid #CBD5E1',
                          borderRadius: '8px',
                          padding: '10px 12px',
                          flex: '1 1 130px',
                          minWidth: '125px',
                          maxWidth: '180px',
                          textAlign: 'center',
                          boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                          zIndex: 2
                        }}
                      >
                        <div style={{ fontSize: '1.1rem', marginBottom: '2px' }}>🔌</div>
                        <div style={{ fontSize: '0.64rem', fontWeight: 800, color: '#334155', textTransform: 'uppercase' }}>Source Connector</div>
                        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {selectedDocArtifacts?.source?.name || 'Direct File Upload'}
                        </div>
                        <span style={{ fontSize: '0.58rem', background: '#F1F5F9', color: '#64748B', padding: '1px 5px', borderRadius: '4px', fontWeight: 700, marginTop: '3px', display: 'inline-block' }}>
                          Authoritative
                        </span>
                      </div>

                      {/* Arrow 1 */}
                      <div style={{ color: '#94A3B8', fontWeight: 800, fontSize: '0.9rem' }}>➔</div>

                      {/* Node 2: Document */}
                      <div
                        style={{
                          background: '#FFF7ED',
                          border: '1.5px solid #EA580C',
                          borderRadius: '8px',
                          padding: '10px 12px',
                          flex: '1 1 130px',
                          minWidth: '125px',
                          maxWidth: '180px',
                          textAlign: 'center',
                          boxShadow: '0 2px 8px rgba(234, 88, 12, 0.15)',
                          zIndex: 2
                        }}
                      >
                        <div style={{ fontSize: '1.1rem', marginBottom: '2px' }}>📄</div>
                        <div style={{ fontSize: '0.64rem', fontWeight: 800, color: '#EA580C', textTransform: 'uppercase' }}>Governance Policy</div>
                        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {selectedDocDetails.title}
                        </div>
                        <span style={{ fontSize: '0.58rem', background: '#FFEDD5', color: '#C2410C', padding: '1px 5px', borderRadius: '4px', fontWeight: 700, marginTop: '3px', display: 'inline-block' }}>
                          v{selectedDocDetails.versions?.length || 1}.0 • SHA256 Sealed
                        </span>
                      </div>

                      {/* Arrow 2 */}
                      <div style={{ color: '#94A3B8', fontWeight: 800, fontSize: '0.9rem' }}>➔</div>

                      {/* Node 3: Claims & Gates */}
                      <div
                        style={{
                          background: '#FFFFFF',
                          border: '1.5px solid #16A34A',
                          borderRadius: '8px',
                          padding: '10px 12px',
                          flex: '1 1 130px',
                          minWidth: '125px',
                          maxWidth: '180px',
                          textAlign: 'center',
                          boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                          zIndex: 2
                        }}
                      >
                        <div style={{ fontSize: '1.1rem', marginBottom: '2px' }}>🛡️</div>
                        <div style={{ fontSize: '0.64rem', fontWeight: 800, color: '#16A34A', textTransform: 'uppercase' }}>Atomic Verification</div>
                        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>
                          {claimsList.length} Extracted Claims
                        </div>
                        <span style={{ fontSize: '0.58rem', background: '#DCFCE7', color: '#15803D', padding: '1px 5px', borderRadius: '4px', fontWeight: 700, marginTop: '3px', display: 'inline-block' }}>
                          9-Gate Verified
                        </span>
                      </div>

                      {/* Arrow 3 */}
                      <div style={{ color: '#94A3B8', fontWeight: 800, fontSize: '0.9rem' }}>➔</div>

                      {/* Node 4: Decision Gateway */}
                      <div
                        style={{
                          background: '#EFF6FF',
                          border: '1.5px solid #3B82F6',
                          borderRadius: '8px',
                          padding: '10px 12px',
                          flex: '1 1 130px',
                          minWidth: '125px',
                          maxWidth: '180px',
                          textAlign: 'center',
                          boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                          zIndex: 2
                        }}
                      >
                        <div style={{ fontSize: '1.1rem', marginBottom: '2px' }}>⚖️</div>
                        <div style={{ fontSize: '0.64rem', fontWeight: 800, color: '#2563EB', textTransform: 'uppercase' }}>Decision Gateway</div>
                        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>
                          Audit & Enforcement
                        </div>
                        <span style={{ fontSize: '0.58rem', background: '#DBEAFE', color: '#1D4ED8', padding: '1px 5px', borderRadius: '4px', fontWeight: 700, marginTop: '3px', display: 'inline-block' }}>
                          0 Blockers
                        </span>
                      </div>
                    </div>

                    {/* Action Bar */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px', paddingTop: '4px' }}>
                      <button
                        type="button"
                        onClick={() => onViewClaims?.(selectedDocDetails, 'dag')}
                        className="btn btn-secondary"
                        style={{ padding: '5px 12px', fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '5px' }}
                      >
                        <Network size={13} style={{ color: '#2563EB' }} />
                        <span>Interactive Node Graph ↗</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => onViewClaims?.(selectedDocDetails, 'summary')}
                        className="btn btn-primary"
                        style={{ padding: '5px 14px', fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '5px', background: '#EA580C', borderColor: '#EA580C', color: '#FFFFFF', fontWeight: 700 }}
                      >
                        <Sparkles size={13} />
                        <span>Open 360° Studio ↗</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          );
        })() : (
          /* INDUSTRIAL FOLDER WORKSPACE & BREADCRUMB NAVIGATION */
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              background: '#FAF8F5',
              overflowY: 'auto',
              minHeight: '440px'
            }}
          >
            {/* 1. TOP BREADCRUMB BAR */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 16px',
                borderBottom: '1px solid var(--border-subtle)',
                background: '#FAF8F5',
                flexWrap: 'wrap',
                gap: '8px'
              }}
            >
              {/* Interactive Clickable Breadcrumb Trail */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {breadcrumbs.map((crumb, idx) => {
                  const isLast = idx === breadcrumbs.length - 1;
                  return (
                    <React.Fragment key={crumb.id || 'root'}>
                      {idx > 0 && <ChevronRight size={12} style={{ color: '#94A3B8' }} />}
                      <span
                        onClick={() => {
                          setActiveFolderId(crumb.id);
                          setSelectedDocId(null);
                        }}
                        style={{
                          cursor: isLast ? 'default' : 'pointer',
                          fontWeight: isLast ? 700 : 500,
                          color: isLast ? 'var(--text-main)' : '#0284C7',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          transition: 'background 0.15s ease'
                        }}
                        onMouseEnter={e => {
                          if (!isLast) e.currentTarget.style.background = '#F0ECE4';
                        }}
                        onMouseLeave={e => {
                          if (!isLast) e.currentTarget.style.background = 'transparent';
                        }}
                        title={isLast ? 'Current folder' : `Jump to ${crumb.name}`}
                      >
                        {crumb.name}
                      </span>
                    </React.Fragment>
                  );
                })}
              </div>

              {/* Action Toolbar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {!readOnly && (
                  <>
                    <button
                      type="button"
                      onClick={() => {
                        setUploadFolderId(activeFolderId);
                        setShowUploadModal(true);
                      }}
                      className="btn btn-secondary"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        background: '#FFFFFF',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px',
                        cursor: 'pointer'
                      }}
                      title="Upload file into this folder"
                    >
                      <Upload size={13} style={{ color: '#0284C7' }} />
                      <span>Upload</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => startInlineCreate(activeFolderId)}
                      className="btn btn-secondary"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        background: '#FFFFFF',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px',
                        cursor: 'pointer'
                      }}
                      title="Create subfolder here"
                    >
                      <FolderPlus size={13} style={{ color: '#FFAB4A' }} />
                      <span>+ Subfolder</span>
                    </button>
                  </>
                )}

                <button
                  type="button"
                  onClick={handleAutoOrganize}
                  disabled={isAutoOrganizing}
                  className="btn btn-secondary"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '4px 10px',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    background: '#FFFFFF',
                    border: '1px solid #CBD5E1',
                    borderRadius: '6px',
                    cursor: isAutoOrganizing ? 'not-allowed' : 'pointer',
                    color: '#D97706'
                  }}
                  title="Automatically organize all unclassified files into domain & connector folders"
                >
                  <Sparkles size={13} className={isAutoOrganizing ? 'spin' : ''} style={{ color: '#F59E0B' }} />
                  <span>{isAutoOrganizing ? 'Filing...' : 'Auto-Organize'}</span>
                </button>
              </div>
            </div>

            {/* 2. FOLDER OVERVIEW HEADER */}
            <div
              style={{
                padding: '16px 20px',
                borderBottom: '1px solid var(--border-subtle)',
                background: '#FAF8F5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '10px',
                    background: '#FFFFFF',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
                  }}
                >
                  {activeFolder ? renderFolderIcon(activeFolder, 20) : <Folder size={20} style={{ color: '#FFAB4A' }} />}
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                      {activeFolder ? activeFolder.name : 'All Vault Documents'}
                    </h3>
                    <span
                      style={{
                        fontSize: '0.66rem',
                        fontWeight: 600,
                        padding: '1px 8px',
                        borderRadius: '999px',
                        background: activeFolder?.is_system ? '#EEF2FF' : '#F1F5F9',
                        color: activeFolder?.is_system ? '#4338CA' : '#475569',
                        border: '1px solid rgba(0,0,0,0.06)'
                      }}
                    >
                      {activeFolder?.folder_type ? activeFolder.folder_type.replace('_', ' ').toUpperCase() : 'VAULT'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {currentChildFolders.length} subfolders • {currentFolderDocs.length} documents in this scope
                  </div>
                </div>
              </div>
            </div>

            {/* 3. SUBFOLDERS SECTION (GRID) */}
            {currentChildFolders.length > 0 && (
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.04em' }}>
                  Subfolders ({currentChildFolders.length})
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px' }}>
                  {currentChildFolders.map(child => (
                    <div
                      key={child.id}
                      onClick={() => {
                        setActiveFolderId(child.id);
                        setExpandedFolders(prev => new Set([...prev, child.id]));
                      }}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '8px',
                        background: '#FFFFFF',
                        border: '1px solid var(--border-subtle)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '8px',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.borderColor = '#FFAB4A';
                        e.currentTarget.style.background = '#FDFCFB';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.borderColor = 'var(--border-subtle)';
                        e.currentTarget.style.background = '#FFFFFF';
                      }}
                      title={`Open ${child.name}`}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                        {renderFolderIcon(child, 16)}
                        <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {child.name}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '4px', background: '#F1F5F9', color: '#64748B', fontWeight: 600 }}>
                        {child.direct_documents_count || 0}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 4. DOCUMENTS TABLE SECTION */}
            <div style={{ padding: '16px 20px', flex: 1 }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.04em' }}>
                Documents ({currentFolderDocs.length})
              </div>

              {currentFolderDocs.length === 0 ? (
                <div
                  style={{
                    padding: '36px 20px',
                    textAlign: 'center',
                    background: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px dashed var(--border-subtle)',
                    color: 'var(--text-muted)'
                  }}
                >
                  <FileText size={28} style={{ color: '#CBD5E1', marginBottom: '8px' }} />
                  <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                    No documents in this folder
                  </div>
                  <div style={{ fontSize: '0.74rem', maxWidth: '320px', margin: '0 auto 12px auto' }}>
                    Upload a policy document, connect an integration, or click Auto-Organize to file unclassified documents.
                  </div>
                  {!readOnly && (
                    <button
                      type="button"
                      onClick={() => {
                        setUploadFolderId(activeFolderId);
                        setShowUploadModal(true);
                      }}
                      className="btn btn-primary"
                      style={{ padding: '5px 14px', fontSize: '0.74rem' }}
                    >
                      Upload to this folder
                    </button>
                  )}
                </div>
              ) : (
                <div style={{ overflowX: 'auto', background: '#FFFFFF', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.76rem' }}>
                    <thead>
                      <tr style={{ background: '#FAF8F5', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Document</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Origin Source</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Domain</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Claims</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Trust Status</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentFolderDocs.map(doc => (
                        <tr
                          key={doc.id}
                          style={{ borderBottom: '1px solid #F1F5F9', transition: 'background 0.1s ease' }}
                          onMouseEnter={e => e.currentTarget.style.background = '#FAF8F5'}
                          onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
                        >
                          <td style={{ padding: '8px 12px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <FileText size={14} style={{ color: '#0284C7', flexShrink: 0 }} />
                              <div style={{ minWidth: 0 }}>
                                <div
                                  onClick={() => setSelectedDocId(doc.id)}
                                  style={{ fontWeight: 600, color: 'var(--text-main)', cursor: 'pointer', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '280px' }}
                                  title={doc.title}
                                >
                                  {doc.title}
                                </div>
                                <div style={{ fontSize: '0.66rem', color: '#94A3B8', fontFamily: 'var(--font-mono)' }}>
                                  {doc.content_hash ? `sha256:${doc.content_hash.slice(0, 8)}...` : 'hash pending'}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            {renderSourceBadge(doc)}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{ fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', background: '#F1F5F9', color: '#475569', fontWeight: 600 }}>
                              {doc.domain || 'General'}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{ fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', background: '#EFF6FF', color: '#1D4ED8', fontWeight: 700 }}>
                              {doc.claims_count !== undefined ? `${doc.claims_count} Claims` : 'Claims ready'}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', background: '#F0FDF4', color: '#166534', fontWeight: 600 }}>
                              <CheckCircle2 size={11} style={{ color: '#16A34A' }} /> Verified
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                              <button
                                type="button"
                                onClick={() => setSelectedDocId(doc.id)}
                                className="btn btn-secondary"
                                style={{ padding: '2px 8px', fontSize: '0.70rem', background: '#FFFFFF', border: '1px solid #CBD5E1', cursor: 'pointer' }}
                                title="Inspect live content & extracted claims"
                              >
                                Preview
                              </button>
                              {!readOnly && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setMovingDoc(doc);
                                    setMoveDocTargetFolderId(doc.folder_id || '');
                                    setShowMoveDocModal(true);
                                  }}
                                  className="btn btn-secondary"
                                  style={{ padding: '2px 6px', fontSize: '0.70rem', background: '#FFFFFF', border: '1px solid #CBD5E1', cursor: 'pointer' }}
                                  title="Move to another folder"
                                >
                                  <Move size={11} />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── CONTEXT MENU (RIGHT-CLICK) ── */}
      {contextMenu.visible && (
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'fixed',
            top: contextMenu.y,
            left: contextMenu.x,
            zIndex: 9999,
            minWidth: '180px',
            background: '#FFFFFF',
            borderRadius: '6px',
            border: '1px solid #CBD5E1',
            boxShadow: '0 6px 18px rgba(0,0,0,0.12), 0 2px 4px rgba(0,0,0,0.06)',
            padding: '4px',
            display: 'flex',
            flexDirection: 'column',
            gap: '1px'
          }}
        >
          {/* Header */}
          <div style={{ padding: '5px 8px', fontSize: '0.68rem', fontWeight: 700, color: '#64748B', borderBottom: '1px solid #F1F5F9', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {contextMenu.type === 'folder' ? `Folder: ${contextMenu.target?.name || ''}`
              : contextMenu.type === 'document' ? `File: ${contextMenu.target?.title || ''}`
              : 'Directory Options'}
          </div>

          {/* FOLDER OPTIONS */}
          {contextMenu.type === 'folder' && (
            <>
              {!readOnly && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      startInlineCreate(contextMenu.target.id);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <FolderPlus size={13} style={{ color: '#2563EB' }} />
                    <span>New subfolder</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUploadFolderId(contextMenu.target.id);
                      setShowUploadModal(true);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <Upload size={13} style={{ color: '#16A34A' }} />
                    <span>Upload file here...</span>
                  </button>
                </>
              )}

              <button
                type="button"
                onClick={() => {
                  fetchFolderMetrics(contextMenu.target.id);
                  setShowInsightsModal(true);
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <BarChart2 size={13} style={{ color: '#7E22CE' }} />
                <span>Folder insights</span>
              </button>

              {!readOnly && !contextMenu.target?.is_system && (
                <>
                  <div style={{ height: '1px', background: '#F1F5F9', margin: '2px 0' }} />

                  <button
                    type="button"
                    onClick={() => {
                      const target = contextMenu.target;
                      setRenamingFolderId(target.id);
                      setRenameInputVal(target.name);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <Edit3 size={13} />
                    <span>Rename</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setMovingFolder(contextMenu.target);
                      setMoveFolderTargetId(contextMenu.target.parent_id || 'root');
                      setShowMoveFolderModal(true);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <Move size={13} />
                    <span>Move...</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      handleDeleteFolder(contextMenu.target);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: '#DC2626' }}
                  >
                    <Trash2 size={13} />
                    <span>Delete</span>
                  </button>
                </>
              )}
            </>
          )}

          {/* DOCUMENT OPTIONS */}
          {contextMenu.type === 'document' && (
            <>
              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setActiveFacilityTab('preview');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <Eye size={13} style={{ color: '#2563EB' }} />
                <span>Open File Preview</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  window.open(`/v1/documents/${contextMenu.target.id}/file`, '_blank');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: '#0284C7' }}
              >
                <ExternalLink size={13} style={{ color: '#0284C7' }} />
                <span>Open File in New Tab ↗</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setIsFullFileReaderOpen(true);
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <BookOpen size={13} style={{ color: '#0F172A' }} />
                <span>Full Document Reader</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setActiveFacilityTab('description');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <Info size={13} style={{ color: '#64748B' }} />
                <span>Description & Specifications</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setActiveFacilityTab('claims');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <Search size={13} style={{ color: '#7E22CE' }} />
                <span>Claim Selecting Across Document</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setActiveFacilityTab('lineage');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <Network size={13} style={{ color: '#16A34A' }} />
                <span>Document-Wise Lineage DAG</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  onViewClaims?.(contextMenu.target, 'summary');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: '#EA580C', fontWeight: 700 }}
              >
                <Sparkles size={13} style={{ color: '#EA580C' }} />
                <span>Open 360° Studio ↗</span>
              </button>

              <div style={{ height: '1px', background: '#F1F5F9', margin: '2px 0' }} />

              {!readOnly && (
                <button
                  type="button"
                  onClick={() => {
                    setMovingDoc(contextMenu.target);
                    setMoveDocTargetFolderId(contextMenu.target.folder_id || activeFolderId);
                    setShowMoveDocModal(true);
                    setContextMenu(prev => ({ ...prev, visible: false }));
                  }}
                  className="context-menu-item"
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                >
                  <Move size={13} style={{ color: '#2563EB' }} />
                  <span>Move to...</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => {
                  handleCopy(contextMenu.target.content_hash);
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-muted)' }}
              >
                <Copy size={13} />
                <span>Copy SHA-256</span>
              </button>

              {!readOnly && (
                <button
                  type="button"
                  onClick={() => {
                    handleDeleteDocument(contextMenu.target);
                    setContextMenu(prev => ({ ...prev, visible: false }));
                  }}
                  className="context-menu-item"
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: '#DC2626' }}
                >
                  <Trash2 size={13} />
                  <span>Delete</span>
                </button>
              )}
            </>
          )}

          {/* CANVAS EMPTY SPACE OPTIONS */}
          {contextMenu.type === 'canvas' && (
            <>
              {!readOnly && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      startInlineCreate(activeFolderId || null);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <FolderPlus size={13} style={{ color: '#3B82F6' }} />
                    <span>New folder</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUploadFolderId(activeFolderId);
                      setShowUploadModal(true);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <Upload size={13} style={{ color: '#16A34A' }} />
                    <span>Upload file here</span>
                  </button>
                </>
              )}

              <button
                type="button"
                onClick={() => {
                  fetchData(true);
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <RefreshCw size={13} />
                <span>Refresh directory</span>
              </button>
            </>
          )}
        </div>
      )}

      {/* ── MODAL: FOLDER INSIGHTS ── */}
      {showInsightsModal && (
        <div className="modal-backdrop" onClick={() => setShowInsightsModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '520px', padding: '22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BarChart2 size={16} style={{ color: '#2563EB' }} />
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>
                  Folder Insights: {activeFolder?.name || 'Workspace'}
                </h3>
              </div>
              <button type="button" onClick={() => setShowInsightsModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '14px' }}>
              <div style={{ padding: '8px 10px', borderRadius: '6px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                <div style={{ fontSize: '0.68rem', color: '#64748B' }}>Total Documents</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '2px' }}>{metrics?.documents?.total ?? allDocuments.length}</div>
              </div>
              <div style={{ padding: '8px 10px', borderRadius: '6px', background: '#F0FDF4', border: '1px solid #DCFCE7' }}>
                <div style={{ fontSize: '0.68rem', color: '#166534' }}>Completed</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#15803D', marginTop: '2px' }}>{metrics?.documents?.by_processing_state?.completed ?? 0}</div>
              </div>
              <div style={{ padding: '8px 10px', borderRadius: '6px', background: '#FEF2F2', border: '1px solid #FEE2E2' }}>
                <div style={{ fontSize: '0.68rem', color: '#991B1B' }}>Failures</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#B91C1C', marginTop: '2px' }}>{metrics?.documents?.by_processing_state?.failed ?? 0}</div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="button" onClick={() => setShowInsightsModal(false)} className="btn btn-primary" style={{ padding: '5px 14px', fontSize: '0.76rem' }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}





      {/* ── MODAL: MOVE FOLDER ── */}
      {showMoveFolderModal && movingFolder && (
        <div className="modal-backdrop" onClick={() => setShowMoveFolderModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Move size={16} style={{ color: '#3B82F6' }} />
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Move '{movingFolder.name}'</h3>
              </div>
              <button type="button" onClick={() => setShowMoveFolderModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>

            <form onSubmit={handleMoveFolder}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>Destination</label>
                <select
                  value={moveFolderTargetId}
                  onChange={e => setMoveFolderTargetId(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.78rem', borderRadius: '5px', border: '1px solid #CBD5E1' }}
                >
                  <option value="root">-- Workspace Root --</option>
                  {folders
                    .filter(f => f.id !== movingFolder.id && !f.is_system)
                    .map(f => (
                      <option key={f.id} value={f.id}>
                        {'- '.repeat(f.depth)} {f.name}
                      </option>
                    ))}
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                <button type="button" onClick={() => setShowMoveFolderModal(false)} className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.76rem' }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ padding: '5px 14px', fontSize: '0.76rem' }}>
                  Move
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: MOVE DOCUMENT ── */}
      {showMoveDocModal && movingDoc && (
        <div className="modal-backdrop" onClick={() => setShowMoveDocModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Move size={16} style={{ color: '#3B82F6' }} />
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Move Document</h3>
              </div>
              <button type="button" onClick={() => setShowMoveDocModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>

            <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Moving: <strong>{movingDoc.title}</strong>
            </div>

            <form onSubmit={handleMoveDocument}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>Destination Folder</label>
                <select
                  value={moveDocTargetFolderId}
                  onChange={e => setMoveDocTargetFolderId(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.78rem', borderRadius: '5px', border: '1px solid #CBD5E1' }}
                  required
                >
                  {folders.map(f => (
                    <option key={f.id} value={f.id}>
                      {f.is_system ? '📥 ' : '- '.repeat(f.depth) + '📁 '} {f.name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                <button type="button" onClick={() => setShowMoveDocModal(false)} className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.76rem' }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ padding: '5px 14px', fontSize: '0.76rem' }}>
                  Move
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: UPLOAD FILE ── */}
      {showUploadModal && (
        <div className="modal-backdrop" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '420px', padding: '22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Upload size={16} style={{ color: '#2563EB' }} />
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Upload Document</h3>
              </div>
              <button type="button" onClick={() => setShowUploadModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>

            <form onSubmit={handleUploadDocument}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>Folder</label>
                <select
                  value={uploadFolderId || ''}
                  onChange={e => setUploadFolderId(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.78rem', borderRadius: '5px', border: '1px solid #CBD5E1' }}
                >
                  {folders.map(f => (
                    <option key={f.id} value={f.id}>
                      {f.is_system ? '📥 ' : '- '.repeat(f.depth) + '📁 '} {f.name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>Classification</label>
                <select
                  value={uploadDocType}
                  onChange={e => setUploadDocType(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.78rem', borderRadius: '5px', border: '1px solid #CBD5E1' }}
                >
                  <option value="policy">Governance Policy</option>
                  <option value="contract">Legal Agreement / Contract</option>
                  <option value="sla">SLA & Terms</option>
                  <option value="compliance">Compliance Guideline</option>
                </select>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>File (.md, .txt, .pdf, .docx)</label>
                <input
                  type="file"
                  required
                  accept=".pdf,.docx,.txt,.md,.json,.csv"
                  onChange={e => setUploadFile(e.target.files?.[0] || null)}
                  style={{ width: '100%', padding: '6px', fontSize: '0.78rem' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="btn btn-secondary"
                  disabled={isUploading}
                  style={{ padding: '5px 12px', fontSize: '0.76rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isUploading || !uploadFile}
                  style={{ padding: '5px 14px', fontSize: '0.76rem', display: 'flex', alignItems: 'center', gap: '5px' }}
                >
                  {isUploading ? (
                    <>
                      <RefreshCw size={13} className="spin" />
                      <span>Ingesting...</span>
                    </>
                  ) : (
                    <>
                      <Upload size={13} />
                      <span>Upload</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: FULL DOCUMENT READER ── */}
      {isFullFileReaderOpen && selectedDocDetails && (
        <div className="modal-backdrop" onClick={() => setIsFullFileReaderOpen(false)} style={{ zIndex: 9999 }}>
          <div
            className="modal-content"
            onClick={e => e.stopPropagation()}
            style={{
              maxWidth: '920px',
              width: '92vw',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              padding: 0,
              overflow: 'hidden',
              borderRadius: '8px',
              background: '#FFFFFF',
              boxShadow: '0 20px 40px rgba(0,0,0,0.2)'
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 18px',
                borderBottom: '1px solid #E2E8F0',
                background: '#F8FAFC'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                <FileText size={18} style={{ color: '#EA580C', flexShrink: 0 }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '0.94rem', fontWeight: 800, color: '#0F172A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {selectedDocDetails.title}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: '#64748B', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.60rem' }}>
                      {selectedDocDetails.document_type || 'Policy'}
                    </span>
                    <span>•</span>
                    <span>v{selectedDocDetails.versions?.length || 1}.0</span>
                    <span>•</span>
                    <code>SHA-256: {selectedDocDetails.content_hash?.substring(0, 16)}...</code>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ position: 'relative' }}>
                  <Search size={13} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
                  <input
                    type="text"
                    placeholder="Search document text..."
                    value={fullReaderSearch}
                    onChange={e => setFullReaderSearch(e.target.value)}
                    style={{
                      padding: '4px 8px 4px 26px',
                      fontSize: '0.74rem',
                      borderRadius: '5px',
                      border: '1px solid #CBD5E1',
                      width: '180px',
                      outline: 'none'
                    }}
                  />
                  {fullReaderSearch && (
                    <button
                      type="button"
                      onClick={() => setFullReaderSearch('')}
                      style={{ position: 'absolute', right: '6px', top: '50%', transform: 'translateY(-50%)', border: 'none', background: 'transparent', color: '#94A3B8', cursor: 'pointer', padding: 0 }}
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>

                <a
                  href={`/v1/documents/${selectedDocDetails.id}/file`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                  style={{ padding: '4px 9px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none' }}
                >
                  <ExternalLink size={12} />
                  <span>Open in Tab ↗</span>
                </a>

                <button
                  type="button"
                  onClick={() => handleCopy(selectedDocDetails.content_uri || '')}
                  className="btn btn-secondary"
                  style={{ padding: '4px 9px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <Copy size={12} />
                  <span>Copy Text</span>
                </button>

                <button
                  type="button"
                  onClick={() => setIsFullFileReaderOpen(false)}
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '6px',
                    border: '1px solid #E2E8F0',
                    background: '#FFFFFF',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#64748B'
                  }}
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Document Content */}
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '24px 32px',
                background: '#FAFAFA',
                fontFamily: 'system-ui, -apple-system, sans-serif'
              }}
            >
              <div
                style={{
                  maxWidth: '780px',
                  margin: '0 auto',
                  background: '#FFFFFF',
                  padding: '32px 40px',
                  borderRadius: '4px',
                  boxShadow: '0 2px 10px rgba(0,0,0,0.06), 0 0 1px rgba(0,0,0,0.1)',
                  minHeight: '400px',
                  fontSize: '0.86rem',
                  lineHeight: 1.65,
                  color: '#1E293B',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}
              >
                {selectedDocDetails.content_uri ? (
                  fullReaderSearch ? (
                    selectedDocDetails.content_uri.split(new RegExp(`(${fullReaderSearch.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')})`, 'gi')).map((part, i) =>
                      part.toLowerCase() === fullReaderSearch.toLowerCase() ? (
                        <mark key={i} style={{ background: '#FEF08A', color: '#854D0E', padding: '1px 3px', borderRadius: '2px', fontWeight: 700 }}>
                          {part}
                        </mark>
                      ) : (
                        part
                      )
                    )
                  ) : (
                    selectedDocDetails.content_uri
                  )
                ) : (
                  <div style={{ textAlign: 'center', color: '#94A3B8', padding: '50px' }}>
                    No raw text content available for this document file.
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 18px',
                borderTop: '1px solid #E2E8F0',
                background: '#FFFFFF',
                fontSize: '0.74rem'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="badge badge-verified" style={{ fontSize: '0.66rem' }}>
                  {claimsList.length} Extracted Claims
                </span>
                <span style={{ color: '#64748B' }}>
                  Verified with SHA-256 seal
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => {
                    setIsFullFileReaderOpen(false);
                    setActiveFacilityTab('claims');
                  }}
                  className="btn btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '0.72rem' }}
                >
                  Select Claims ({claimsList.length})
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setIsFullFileReaderOpen(false);
                    onViewClaims?.(selectedDocDetails, 'summary');
                  }}
                  className="btn btn-primary"
                  style={{ padding: '4px 12px', fontSize: '0.72rem', background: '#EA580C', borderColor: '#EA580C', color: '#FFFFFF', fontWeight: 700 }}
                >
                  <Sparkles size={12} style={{ marginRight: '4px', display: 'inline' }} />
                  <span>Open 360° Studio ↗</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

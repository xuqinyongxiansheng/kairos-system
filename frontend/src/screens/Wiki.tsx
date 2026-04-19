/**
 * Wiki知识库管理页面
 *
 * 提供完整的Wiki文档CRUD操作界面，包括：
 * - 文档列表（支持分页、筛选）
 * - 创建/编辑/删除文档
 * - 语义搜索
 * - 自然语言查询
 *
 * 使用方式：在路由中引入此组件即可显示完整的Wiki管理界面。
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Text, Box, useInput, useApp } from 'ink';
import Spinner from '../components/Spinner.js';
import { localBackend, type WikiDocument, type WikiSearchResult } from '../services/api/localBackend.js';

// ==================== 类型定义 ====================

type ViewMode = 'list' | 'create' | 'view' | 'edit' | 'search' | 'query';

interface WikiPageProps {
  onClose?: () => void;
}

// ==================== 主组件 ====================

export function WikiPage({ onClose }: WikiPageProps): JSX.Element {
  const { exit } = useApp();
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [documents, setDocuments] = useState<WikiDocument[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<WikiDocument | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<WikiSearchResult[]>([]);
  const [queryQuestion, setQueryQuestion] = useState('');
  const [queryAnswer, setQueryAnswer] = useState<string | null>(null);

  // 表单状态
  const [formTitle, setFormTitle] = useState('');
  const [formContent, setFormContent] = useState('');
  const [formSource, setFormSource] = useState('custom');

  // 加载文档列表
  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await localBackend.listDocuments(undefined, limit, page * limit);
      setDocuments(result.documents);
      setTotal(result.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [page, limit]);

  // 初始加载
  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // 键盘导航
  useInput((input, key) => {
    if (key.escape || (key.ctrl && input === 'c')) {
      onClose?.() || exit();
      return;
    }

    switch (viewMode) {
      case 'list':
        if (input === 'n' || input === 'N') {
          handleCreate();
        } else if (input === 's' || input === 'S') {
          setViewMode('search');
          setSearchQuery('');
        } else if (input === 'q' || input === 'Q') {
          setViewMode('query');
          setQueryQuestion('');
        } else if ((key.leftArrow || input === 'h') && page > 0) {
          setPage(p => p - 1);
        } else if ((key.rightArrow || input === 'l') && (page + 1) * limit < total) {
          setPage(p => p + 1);
        }
        break;
      case 'create':
      case 'edit':
        if (key.ctrl && input === 's') {
          handleSave();
        }
        break;
      case 'view':
        if (input === 'e' || input === 'E') {
          setViewMode('edit');
        } else if (input === 'd' || input === 'D') {
          handleDelete();
        } else if (input === 'b' || input === 'B') {
          setViewMode('list');
        }
        break;
      case 'search':
        if (key.return && searchQuery.trim()) {
          handleSearch();
        } else if (input === 'b' || input === 'B') {
          setViewMode('list');
        }
        break;
      case 'query':
        if (key.return && queryQuestion.trim()) {
          handleQuery();
        } else if (input === 'b' || input === 'B') {
          setViewMode('list');
        }
        break;
    }
  });

  // 处理创建新文档
  const handleCreate = () => {
    setFormTitle('');
    setFormContent('');
    setFormSource('custom');
    setSelectedDoc(null);
    setViewMode('create');
  };

  // 处理保存
  const handleSave = async () => {
    if (!formTitle.trim() || !formContent.trim()) return;

    setLoading(true);
    setError(null);
    try {
      if (viewMode === 'edit' && selectedDoc) {
        // 编辑模式：先删除再重新添加（因为后端没有PUT端点）
        await localBackend.deleteDocument(selectedDoc.id);
      }

      await localBackend.addDocument({
        title: formTitle,
        content: formContent,
        source: formSource,
      });

      await loadDocuments();
      setViewMode('list');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save document');
    } finally {
      setLoading(false);
    }
  };

  // 处理删除
  const handleDelete = async () => {
    if (!selectedDoc) return;

    setLoading(true);
    setError(null);
    try {
      await localBackend.deleteDocument(selectedDoc.id);
      await loadDocuments();
      setViewMode('list');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    } finally {
      setLoading(false);
    }
  };

  // 处理搜索
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const results = await localBackend.searchDocuments(searchQuery, 10);
      setSearchResults(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  // 处理自然语言查询
  const handleQuery = async () => {
    if (!queryQuestion.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const result = await localBackend.queryDocuments({
        question: queryQuestion,
        top_k: 5,
        generate_answer: true,
      });
      setQueryAnswer(JSON.stringify(result, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  // 渲染不同视图
  const renderContent = (): React.ReactNode => {
    if (loading) {
      return (
        <Box padding={1}>
          <Spinner />
          <Text> Loading...</Text>
        </Box>
      );
    }

    if (error) {
      return (
        <Box padding={1} backgroundColor="red">
          <Text color="white">[ERROR] {error}</Text>
        </Box>
      );
    }

    switch (viewMode) {
      case 'list':
        return renderListView();
      case 'create':
      case 'edit':
        return renderFormView();
      case 'view':
        return renderDetailView();
      case 'search':
        return renderSearchView();
      case 'query':
        return renderQueryView();
      default:
        return null;
    }
  };

  // 渲染列表视图
  const renderListView = (): JSX.Element => {
    const totalPages = Math.ceil(total / limit);

    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>
        <Text bold color="blue"> Wiki Knowledge Base Management</Text>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>

        <Box marginTop={1} marginBottom={1}>
          <Text dimColor>Total: {total} documents</Text>
        </Box>

        {/* 操作提示 */}
        <Box marginBottom={1}>
          <Text color="green">
            [N]ew | [S]earch | [Q]uery | Esc:Exit | h/l:Page ({page + 1}/{totalPages})
          </Text>
        </Box>

        {/* 文档列表 */}
        {documents.length === 0 ? (
          <Box padding={1}>
            <Text dimColor>No documents found. Press 'N' to create one.</Text>
          </Box>
        ) : (
          documents.map((doc, index) => (
            <Box
              key={doc.id}
              marginBottom={1}
              paddingX={1}
              borderStyle="round"
              flexDirection="column"
            >
              <Box>
                <Text bold>{index + 1}. {doc.title}</Text>
              </Box>
              <Box>
                <Text dimColor>ID: {doc.id.substring(0, 8)}... | Type: {doc.source_type} | Updated: {new Date(doc.updated_at).toLocaleDateString()}</Text>
              </Box>
              <Box>
                <Text dimColor>{doc.content.substring(0, 100)}{doc.content.length > 100 ? '...' : ''}</Text>
              </Box>
              <Box>
                <Text color="yellow">[Enter to View]</Text>
              </Box>
            </Box>
          ))
        )}
      </Box>
    );
  };

  // 渲染表单视图（创建/编辑）
  const renderFormView = (): JSX.Element => {
    const isEdit = viewMode === 'edit';

    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>
        <Text bold color="blue">{isEdit ? 'Edit Document' : 'Create New Document'}</Text>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>

        <Box marginTop={1} flexDirection="column">
          <Box marginBottom={1}>
            <Text bold>Title:</Text>
            <Text color="cyan">{formTitle || '(enter title)'}</Text>
          </Box>

          <Box marginBottom={1}>
            <Text bold>Content:</Text>
            <Text color="cyan">{formContent || '(enter content)'}</Text>
          </Box>

          <Box marginBottom={1}>
            <Text bold>Source:</Text>
            <Text color="cyan">{formSource}</Text>
          </Box>
        </Box>

        <Box marginTop={1}>
          <Text color="green">Ctrl+S: Save | Esc: Cancel</Text>
        </Box>
      </Box>
    );
  };

  // 渲染详情视图
  const renderDetailView = (): JSX.Element => {
    if (!selectedDoc) return <Text>No document selected</Text>;

    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>
        <Text bold color="blue">Document Details</Text>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>

        <Box marginTop={1} flexDirection="column">
          <Box marginBottom={1}>
            <Text bold>Title: </Text>
            <Text>{selectedDoc.title}</Text>
          </Box>

          <Box marginBottom={1}>
            <Text bold>ID: </Text>
            <Text dimColor>{selectedDoc.id}</Text>
          </Box>

          <Box marginBottom={1}>
            <Text bold>Type: </Text>
            <Text>{selectedDoc.source_type}</Text>
          </Box>

          <Box marginBottom={1}>
            <Text bold>Created: </Text>
            <Text>{new Date(selectedDoc.created_at).toLocaleString()}</Text>
          </Box>

          <Box marginBottom={1}>
            <Text bold>Updated: </Text>
            <Text>{new Date(selectedDoc.updated_at).toLocaleString()}</Text>
          </Box>

          <Box marginTop={1} marginBottom={1}>
            <Text bold>Content:</Text>
            <Text>{selectedDoc.content}</Text>
          </Box>
        </Box>

        <Box marginTop={1}>
          <Text color="green">[E]dit | [D]elete | [B]ack | Esc:Exit</Text>
        </Box>
      </Box>
    );
  };

  // 渲染搜索视图
  const renderSearchView = (): JSX.Element => {
    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>
        <Text bold color="blue">Search Documents</Text>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>

        <Box marginTop={1} marginBottom={1}>
          <Text bold>Query: </Text>
          <Text color="cyan">{searchQuery || '(type search query and press Enter)'}</Text>
        </Box>

        {searchResults.length > 0 && (
          <Box flexDirection="column" marginTop={1}>
            <Text bold>Results ({searchResults.length}):</Text>
            {searchResults.map((result, index) => (
              <Box key={index} marginBottom={1} paddingX={1}>
                <Text bold>{index + 1}. {result.title}</Text>
                <Text dimColor>Score: {(result.score * 100).toFixed(1)}%</Text>
                <Text>{result.snippet}</Text>
              </Box>
            ))}
          </Box>
        )}

        <Box marginTop={1}>
          <Text color="green">Enter: Search | B: Back | Esc: Exit</Text>
        </Box>
      </Box>
    );
  };

  // 渲染查询视图
  const renderQueryView = (): JSX.Element => {
    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>
        <Text bold color="blue">Natural Language Query</Text>
        <Text bold color="blue">
          {'=' .repeat(50)}
        </Text>

        <Box marginTop={1} marginBottom={1}>
          <Text bold>Question: </Text>
          <Text color="cyan">{queryQuestion || '(type your question and press Enter)'}</Text>
        </Box>

        {queryAnswer && (
          <Box flexDirection="column" marginTop={1} paddingX={1} borderStyle="round">
            <Text bold>AI Answer:</Text>
            <Text>{queryAnswer}</Text>
          </Box>
        )}

        <Box marginTop={1}>
          <Text color="green">Enter: Query | B: Back | Esc: Exit</Text>
        </Box>
      </Box>
    );
  };

  return (
    <Box flexDirection="column" height="100%">
      {renderContent()}
    </Box>
  );
}

export default WikiPage;

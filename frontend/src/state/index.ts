/**
 * 状态管理统一导出
 *
 * 所有状态分片和Actions通过此文件统一导出，
 * 组件只需从此处导入，无需关心内部实现。
 */

export { Store, DerivedStore, useStore, useDerived } from './core'
export type { Listener, Unsubscribe, StoreConfig } from './core'

export {
  connectionStore,
  systemStore,
  chatStore,
  wikiStore,
  uiStore,
  connectionActions,
  systemActions,
  chatActions,
  wikiActions,
  uiActions,
} from './slices'

export type {
  ConnectionState,
  SystemState,
  ChatState,
  ChatMessage,
  WikiState,
  UIState,
  AppRoute,
  Notification,
} from './slices'

/**
 * 颜色差异模块（降级实现）
 *
 * 原始实现依赖 color-diff-napi 原生模块，
 * 此为降级版本，不依赖原生模块。
 */

import { isEnvDefinedFalsy } from '../../utils/envUtils.js'

export type ColorModuleUnavailableReason = 'env' | 'native_unavailable'

export function getColorModuleUnavailableReason(): ColorModuleUnavailableReason | null {
  if (isEnvDefinedFalsy(process.env.CLAUDE_CODE_SYNTAX_HIGHLIGHT)) {
    return 'env'
  }
  return 'native_unavailable'
}

export function expectColorDiff(): any | null {
  return null
}

export function expectColorFile(): any | null {
  return null
}

export function getSyntaxTheme(themeName: string): any | null {
  return null
}

// yoga-layout/index.js - Yoga 布局引擎存根
// 提供 Yoga 节点创建和布局计算功能

export const OVERFLOW = {
  VISIBLE: 0,
  HIDDEN: 1,
  SCROLL: 2,
}

export const Overflow = OVERFLOW

export const FLEX_DIRECTION = {
  COLUMN: 0,
  COLUMN_REVERSE: 1,
  ROW: 2,
  ROW_REVERSE: 3,
}

export const FlexDirection = FLEX_DIRECTION

export const ALIGN = {
  AUTO: 0,
  FLEX_START: 1,
  CENTER: 2,
  FLEX_END: 3,
  STRETCH: 4,
  BASELINE: 5,
  SPACE_BETWEEN: 6,
  SPACE_AROUND: 7,
}

export const Align = ALIGN

export const JUSTIFY = {
  FLEX_START: 0,
  CENTER: 1,
  FLEX_END: 2,
  SPACE_BETWEEN: 3,
  SPACE_AROUND: 4,
  SPACE_EVENLY: 5,
}

export const Justify = JUSTIFY

export const POSITION_TYPE = {
  RELATIVE: 0,
  ABSOLUTE: 1,
}

export const PositionType = POSITION_TYPE

export const DISPLAY = {
  FLEX: 0,
  NONE: 1,
}

export const Display = DISPLAY

export const EDGE = {
  LEFT: 0,
  TOP: 1,
  RIGHT: 2,
  BOTTOM: 3,
  START: 4,
  END: 5,
  HORIZONTAL: 6,
  VERTICAL: 7,
  ALL: 8,
}

export const Edge = EDGE

export const DIRECTION = {
  INHERIT: 0,
  LTR: 1,
  RTL: 2,
}

export const Direction = DIRECTION

export const GUTTER = {
  COLUMN: 0,
  ROW: 1,
  ALL: 2,
}

export const Gutter = GUTTER

export const WRAP = {
  NO_WRAP: 0,
  WRAP: 1,
  WRAP_REVERSE: 2,
}

export const Wrap = WRAP

export const MEASURE_MODE = {
  UNDEFINED: 0,
  EXACTLY: 1,
  AT_MOST: 2,
}

export const MeasureMode = MEASURE_MODE

class YogaNode {
  constructor() {
    this._width = 0
    this._height = 0
    this._children = []
  }

  static create() { return new YogaNode() }

  setWidth(value) { this._width = value; return this }
  setHeight(value) { this._height = value; return this }
  setFlexDirection() { return this }
  setAlignItems() { return this }
  setJustifyContent() { return this }
  setPadding() { return this }
  setMargin() { return this }
  setGap() { return this }
  setFlexGrow() { return this }
  setFlexShrink() { return this }
  setFlexBasis() { return this }
  setPositionType() { return this }
  setPosition() { return this }
  setOverflow() { return this }
  setDisplay() { return this }
  setWrap() { return this }
  setDirection() { return this }
  setMinWidth() { return this }
  setMinHeight() { return this }
  setMaxWidth() { return this }
  setMaxHeight() { return this }
  insertChild(child, index) { this._children.splice(index, 0, child) }
  removeChild(child) {
    const idx = this._children.indexOf(child)
    if (idx !== -1) this._children.splice(idx, 1)
  }
  calculateLayout(width, height, direction) {}
  getComputedLeft() { return 0 }
  getComputedTop() { return 0 }
  getComputedWidth() { return this._width || 100 }
  getComputedHeight() { return this._height || 20 }
  getComputedMargin() { return 0 }
  getComputedPadding() { return 0 }
  getComputedBorder() { return 0 }
  getDisplay() { return 1 }
  getFlexDirection() { return 0 }
  getAlignItems() { return 1 }
  getJustifyContent() { return 0 }
  getWrap() { return 0 }
  getOverflow() { return 0 }
  getPositionType() { return 0 }
  getFlexGrow() { return 0 }
  getFlexShrink() { return 0 }
  getFlexBasis() { return NaN }
  getGap() { return 0 }
  getStyle() { return {} }
  isReferenceBaseline() { return false }
  setReferenceBaseline() {}
  copyStyle() {}
  getChild(index) { return this._children[index] || null }
  reset() {}
  getChildCount() { return this._children.length }
  free() {}
  destroy() {}
}

export const Node = YogaNode

export function createNode() {
  return new YogaNode()
}

let _createCount = 0
let _destroyCount = 0

export function getYogaCounters() {
  return {
    createCount: _createCount,
    destroyCount: _destroyCount,
  }
}

const Yoga = {
  createNode,
  Node,
  YogaNode,
  OVERFLOW,
  Overflow,
  FLEX_DIRECTION,
  FlexDirection,
  ALIGN,
  Align,
  JUSTIFY,
  Justify,
  POSITION_TYPE,
  PositionType,
  DISPLAY,
  Display,
  EDGE,
  Edge,
  DIRECTION,
  Direction,
  GUTTER,
  Gutter,
  WRAP,
  Wrap,
  MEASURE_MODE,
  MeasureMode,
  getYogaCounters,
}

export default Yoga

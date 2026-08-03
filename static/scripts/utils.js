import { UUID_PATTERN } from "./constants.js"

export const formatValue = (value) =>
  value == null ? "—" : Array.isArray(value) ? `[${value}]` : String(value)

export const abbreviateId = (value) => {
  if (value == null) return "—"
  const str = String(value)
  return str.length === 36 ? str.slice(0, 8) : str
}

export const abbreviateField = (value) => {
  if (value == null) return "—"

  if (Array.isArray(value)) {
    return value
      .map((item) =>
        UUID_PATTERN.test(String(item)) ? String(item).slice(0, 8) : item,
      )
      .join(", ")
  }

  if (typeof value === "number" && !Number.isInteger(value)) {
    return value.toFixed(2)
  }

  return UUID_PATTERN.test(String(value)) ? String(value).slice(0, 8) : value
}

const TEMP_MIN_C = -10
const TEMP_MAX_C = 40
export const toCelsius = (fraction) =>
  TEMP_MIN_C + fraction * (TEMP_MAX_C - TEMP_MIN_C)

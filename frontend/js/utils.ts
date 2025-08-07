// import { useState } from "react";
import { LngLatBounds } from "maplibre-gl";

export const useDarkMode = () => {
  return false;
};

export function getFont(theme: string) {
  if (theme === "positron") {
    return ["Source Sans Pro Regular"];
  }
  if (theme === "dark_matter") {
    return ["Noto Sans Regular"];
  }
  if (theme === "satellite") {
    return ["Noto Sans Regular"];
  }
  return ["Noto Sans Regular"];
}

export function getBounds<T>(
  list: Array<T> | undefined,
  key: (arg0: T) => [number, number] | null | undefined,
  initialBounds?: LngLatBounds,
) {
  if (list?.length) {
    const bounds = initialBounds || new LngLatBounds();
    list.reduce((bounds, item?) => {
      if (item) {
        const value = key(item);
        if (value) {
          bounds.extend(value);
        }
      }
      return bounds;
    }, bounds);
    return bounds;
  }
}

import { type DependencyList, useEffect, useRef } from "react";

export function useAutosizeTextarea(maxHeight: number, dependencies: DependencyList) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    resizeTextareaToContent(textareaRef.current, maxHeight);
  }, dependencies);

  return textareaRef;
}

function resizeTextareaToContent(element: HTMLTextAreaElement | null, maxHeight: number) {
  if (!element) {
    return;
  }
  element.style.height = "auto";
  const nextHeight = Math.min(element.scrollHeight, maxHeight);
  element.style.height = nextHeight + "px";
  element.style.overflowY = element.scrollHeight > maxHeight ? "auto" : "hidden";
  element.style.overflowX = "hidden";
}

import { type DependencyList, type RefObject, type UIEvent, useEffect, useRef } from "react";

type ThreadScrollFollow = {
  threadRef: RefObject<HTMLDivElement | null>;
  handleThreadScroll: (event: UIEvent<HTMLDivElement>) => void;
  resetThreadScrollFollow: () => void;
  scrollThreadToBottom: () => void;
};

export function useThreadScrollFollow(scrollDependencies: DependencyList, resetDependencies: DependencyList): ThreadScrollFollow {
  const threadRef = useRef<HTMLDivElement | null>(null);
  const autoScrollEnabledRef = useRef(true);

  useEffect(() => {
    const element = threadRef.current;
    if (element && autoScrollEnabledRef.current) {
      element.scrollTop = element.scrollHeight;
    }
  }, scrollDependencies);

  useEffect(() => {
    resetThreadScrollFollow();
    window.requestAnimationFrame(() => {
      scrollThreadToBottom();
    });
  }, resetDependencies);

  function handleThreadScroll(event: UIEvent<HTMLDivElement>) {
    autoScrollEnabledRef.current = isNearScrollBottom(event.currentTarget);
  }

  function resetThreadScrollFollow() {
    autoScrollEnabledRef.current = true;
  }

  function scrollThreadToBottom() {
    const element = threadRef.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }

  return { threadRef, handleThreadScroll, resetThreadScrollFollow, scrollThreadToBottom };
}

function isNearScrollBottom(element: HTMLElement) {
  return element.scrollHeight - element.scrollTop - element.clientHeight < 32;
}

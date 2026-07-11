import { type DependencyList, type RefObject, type UIEvent, useEffect, useRef } from "react";

type ThreadScrollFollow = {
  threadRef: RefObject<HTMLDivElement | null>;
  handleThreadScroll: (event: UIEvent<HTMLDivElement>) => void;
  resetThreadScrollFollow: () => void;
  scrollThreadToBottom: () => void;
};

const SCROLL_BOTTOM_TOLERANCE_PX = 48;
const SCROLL_UP_TOLERANCE_PX = 2;

export function useThreadScrollFollow(scrollDependencies: DependencyList, resetDependencies: DependencyList): ThreadScrollFollow {
  const threadRef = useRef<HTMLDivElement | null>(null);
  const autoScrollEnabledRef = useRef(true);
  const lastScrollTopRef = useRef(0);
  const pendingFrameRef = useRef<number | null>(null);

  useEffect(() => {
    followBottomIfEnabled();
  }, scrollDependencies);

  useEffect(() => {
    const element = threadRef.current;
    if (!element) {
      return;
    }

    const observer = new ResizeObserver(() => {
      followBottomIfEnabled();
    });
    observer.observe(element);
    if (element.firstElementChild) {
      observer.observe(element.firstElementChild);
    }

    return () => {
      observer.disconnect();
      if (pendingFrameRef.current !== null) {
        window.cancelAnimationFrame(pendingFrameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    resetThreadScrollFollow();
    window.requestAnimationFrame(() => {
      scrollThreadToBottom();
    });
  }, resetDependencies);

  function handleThreadScroll(event: UIEvent<HTMLDivElement>) {
    const element = event.currentTarget;
    const isNearBottom = isNearScrollBottom(element);
    const isScrollingUp = element.scrollTop < lastScrollTopRef.current - SCROLL_UP_TOLERANCE_PX;

    if (isNearBottom) {
      autoScrollEnabledRef.current = true;
    } else if (isScrollingUp) {
      autoScrollEnabledRef.current = false;
    }

    lastScrollTopRef.current = element.scrollTop;
  }

  function resetThreadScrollFollow() {
    autoScrollEnabledRef.current = true;
  }

  function scrollThreadToBottom() {
    const element = threadRef.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
      lastScrollTopRef.current = element.scrollTop;
    }
  }

  function followBottomIfEnabled() {
    if (!autoScrollEnabledRef.current) {
      return;
    }
    if (pendingFrameRef.current !== null) {
      window.cancelAnimationFrame(pendingFrameRef.current);
    }
    pendingFrameRef.current = window.requestAnimationFrame(() => {
      pendingFrameRef.current = null;
      scrollThreadToBottom();
    });
  }

  return { threadRef, handleThreadScroll, resetThreadScrollFollow, scrollThreadToBottom };
}

function isNearScrollBottom(element: HTMLElement) {
  return element.scrollHeight - element.scrollTop - element.clientHeight < SCROLL_BOTTOM_TOLERANCE_PX;
}

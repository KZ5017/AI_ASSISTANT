import { type DependencyList, type RefObject, type UIEvent, useEffect, useRef, useState } from "react";

type ThreadScrollFollow = {
  threadRef: RefObject<HTMLDivElement | null>;
  handleThreadScroll: (event: UIEvent<HTMLDivElement>) => void;
  resetThreadScrollFollow: () => void;
  scrollThreadToBottom: (behavior?: ScrollBehavior) => void;
  isThreadAtBottom: boolean;
};

const SCROLL_BOTTOM_TOLERANCE_PX = 48;
const SCROLL_UP_TOLERANCE_PX = 2;

export function useThreadScrollFollow(scrollDependencies: DependencyList, resetDependencies: DependencyList): ThreadScrollFollow {
  const threadRef = useRef<HTMLDivElement | null>(null);
  const autoScrollEnabledRef = useRef(true);
  const lastScrollTopRef = useRef(0);
  const pendingFrameRef = useRef<number | null>(null);
  const [isThreadAtBottom, setIsThreadAtBottom] = useState(true);

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

    setIsThreadAtBottom(isNearBottom);

    if (isNearBottom) {
      autoScrollEnabledRef.current = true;
    } else if (isScrollingUp) {
      autoScrollEnabledRef.current = false;
    }

    lastScrollTopRef.current = element.scrollTop;
  }

  function resetThreadScrollFollow() {
    autoScrollEnabledRef.current = true;
    setIsThreadAtBottom(true);
  }

  function scrollThreadToBottom(behavior: ScrollBehavior = "auto") {
    const element = threadRef.current;
    if (element) {
      if (behavior === "smooth") {
        element.scrollTo({ top: element.scrollHeight, behavior });
      } else {
        element.scrollTop = element.scrollHeight;
      }
      lastScrollTopRef.current = element.scrollTop;
      autoScrollEnabledRef.current = true;
      setIsThreadAtBottom(true);
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

  return { threadRef, handleThreadScroll, resetThreadScrollFollow, scrollThreadToBottom, isThreadAtBottom };
}

function isNearScrollBottom(element: HTMLElement) {
  return element.scrollHeight - element.scrollTop - element.clientHeight < SCROLL_BOTTOM_TOLERANCE_PX;
}

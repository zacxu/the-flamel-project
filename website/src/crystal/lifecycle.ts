/** A renderer has one frame owner. Idle, hidden and off-screen viewers own no RAF. */
export interface FrameDriver {
  requestFrame: (callback: (time: number) => void) => number;
  cancelFrame: (handle: number) => void;
  render: (deltaSeconds: number) => void;
  onError: (error: unknown) => void;
}

export function createFrameOwner(driver: FrameDriver) {
  let disposed = false;
  let visible = true;
  let hidden = false;
  let continuous = false;
  let pending: number | null = null;
  let epoch = 0;
  let previousTime: number | null = null;
  const active = () => !disposed && visible && !hidden;
  function cancel() {
    epoch += 1;
    if (pending !== null) driver.cancelFrame(pending);
    pending = null;
    previousTime = null;
  }
  function invalidate() {
    if (!active() || pending !== null) return;
    const token = epoch;
    pending = driver.requestFrame(time => {
      if (disposed || token !== epoch || !active()) return;
      pending = null;
      const delta = previousTime === null ? 0 : Math.min(0.1, Math.max(0, (time - previousTime) / 1000));
      previousTime = time;
      try { driver.render(delta); }
      catch (error) { cancel(); driver.onError(error); return; }
      if (continuous) invalidate();
      else previousTime = null;
    });
  }
  function synchronize() {
    if (!active()) cancel();
    else invalidate();
  }
  return {
    invalidate,
    setVisible(value: boolean) { visible = value; synchronize(); },
    setHidden(value: boolean) { hidden = value; synchronize(); },
    setContinuous(value: boolean) {
      continuous = value;
      // An outstanding one-off render may finish, but a disabled loop never renews itself.
      if (!value) previousTime = null;
      if (value) synchronize();
    },
    dispose() { if (!disposed) { disposed = true; cancel(); } },
    get disposed() { return disposed; },
    get scheduled() { return pending !== null; },
  };
}

/** Cleanup is reverse-order and idempotent, including partially constructed renderers. */
export function createResourceScope() {
  let disposed = false;
  const cleanups: (() => void)[] = [];
  return {
    defer(cleanup: () => void) {
      if (disposed) cleanup();
      else cleanups.push(cleanup);
    },
    dispose(): readonly unknown[] {
      if (disposed) return [];
      disposed = true;
      const failures: unknown[] = [];
      for (const cleanup of cleanups.reverse()) {
        try { cleanup(); } catch (error) { failures.push(error); }
      }
      cleanups.length = 0;
      return failures;
    },
    get disposed() { return disposed; },
  };
}

/** Used for context loss and construction/render exceptions; the fallback is reported once. */
export function createFailureGate(dispose: () => void, report: (reason: string) => void) {
  let reported = false;
  return (reason: string, event?: { preventDefault: () => void }) => {
    event?.preventDefault();
    if (reported) return;
    reported = true;
    dispose();
    report(reason);
  };
}

export async function runLegacyRecallWithTimeout<T>(params: {
  work: () => Promise<T>;
  timeoutMs: number;
  onTimeout: () => void;
}): Promise<T | undefined> {
  const { work, timeoutMs, onTimeout } = params;

  return new Promise<T | undefined>((resolve, reject) => {
    let settled = false;
    const timeoutHandle = setTimeout(() => {
      if (settled) return;
      settled = true;
      onTimeout();
      resolve(undefined);
    }, timeoutMs);

    work().then(
      (value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timeoutHandle);
        resolve(value);
      },
      (error) => {
        if (settled) return;
        settled = true;
        clearTimeout(timeoutHandle);
        reject(error);
      },
    );
  });
}

(jina-on-windows)=
# Jina on Windows

You can install and use Jina on Windows.

However, as Jina is built keeping *nix-based platforms in mind, and the upstream libraries that Jina depends on also follow the similar ideology. Hence, there are some caveats when running Jina on Windows. [If you face additional issues, please let us know.](https://github.com/jina-ai/jina/issues/)

```{caution}
There can be a significant performance impact while running Jina on Windows. You may not want to use it in production.
```

```{tip}
Alternatively, you can use the Windows Subsystem for Linux, for better compatibility. Check the official guide [here](https://docs.microsoft.com/en-us/windows/wsl/install).
Make sure you install WSL**2**.
Once done, you can install Jina as on a native *nix platform.
```

## Known issues

### `multiprocessing spawn`

Jina relies heavily on `multiprocessing` to enable scaling & distribution. Windows only supports [spawn start method for multiprocessing](https://docs.python.org/3/library/multiprocessing.html#the-spawn-and-forkserver-start-methods), which has a few caveats. [Please follow the guidelines here.](../../../fundamentals/flow/remarks#multiprocessing-spawn)

### Compatability of Executors in the Hub

We've added preliminary support to using Executors listed in the Hub portal. Note that, these Executors are based on *nix OS and might not be compatible to run natively on Windows. Containers that are built on Windows OS are not supported yet. 


```{seealso}
[Install Docker Desktop on Windows](https://docs.docker.com/desktop/windows/install/)
```

### JinaD is not supported

We haven't added suppoort to JinaD on Windows. If you can make it work, feel free to create a PR.

### Limited support for `DocumentArrayMemmap`

Even though support for [DocumentArrayMemmap](../../fundamentals/document/documentarraymemmap-api) is added, it is error prone. Please proceed with caution.

### Memory watermark is unavailable 

Since Windows doesn't support `resource` module, memory watermark checks are disabled by default.


### `UnicodeEncodeError` on Jina CLI

```bash
UnicodeEncodeError: 'charmap' codec can't encode character '\u25ae' in position : character maps to <undefined>
```
Set environment variable `PYTHONIOENCODING='utf-8'` before starting your python script.


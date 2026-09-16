## Installation

### Windows

1. Download the latest MSTTools release from the **Releases** section.
2. Extract the downloaded ZIP file.
3. Open Command Prompt or PowerShell inside the extracted folder.
4. Install MSTTools:

```bash
python -m pip install .
```

5. After installation, launch MSTTools from any directory:

```bash
mst
```

MSTTools only needs to be installed once.

### Verify Installation

Check that MSTTools was installed correctly:

```bash
mst --version
```

You should see:

```text
MSTTools 1.1.0
```

### Using MSTTools

Navigate to a project you want to inspect:

```bash
cd C:\Projects\MyProject
```

Then run:

```bash
mst
```

MSTTools will analyze the current directory and open the interactive terminal menu.

For example:

```text
C:\Projects\Project-A> mst
C:\Projects\Project-B> mst
C:\Projects\Project-C> mst
```

You do not need to copy MSTTools into each project.

### Windows PATH Troubleshooting

If installation succeeds but Windows displays:

```text
'mst' is not recognized as an internal or external command
```

look at the warning printed during installation. Python may show a path similar to:

```text
...\Python312\Scripts
```

Add the exact `Scripts` directory shown on your computer to your user `PATH`.

Then close and reopen Command Prompt and verify:

```bash
where mst
```

If `mst.exe` is found, run:

```bash
mst
```

### Uninstall

To remove MSTTools:

```bash
python -m pip uninstall msttools-cli
```

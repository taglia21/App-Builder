from typing import Dict

import httpx


class LivePreviewService:
    """Live preview service for generated applications."""

    def __init__(self):
        self.preview_port_start = 8100
        self.active_previews = {}
        self.codesandbox_api = 'https://codesandbox.io/api/v1'

    async def create_sandbox_preview(self, files: Dict[str, str], framework: str = 'python') -> Dict:
        """Create a CodeSandbox preview for the application."""
        try:
            # Format files for CodeSandbox
            sandbox_files = {}
            for path, content in files.items():
                sandbox_files[path] = {'content': content}

            # Add package.json for web apps
            if framework in ['react', 'vue', 'nextjs']:
                if 'package.json' not in sandbox_files:
                    sandbox_files['package.json'] = {
                        'content': self._generate_package_json(framework)
                    }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'{self.codesandbox_api}/sandboxes/define',
                    json={'files': sandbox_files},
                    params={'json': 1}
                )

                if response.status_code == 200:
                    data = response.json()
                    sandbox_id = data.get('sandbox_id')
                    return {
                        'success': True,
                        'sandbox_id': sandbox_id,
                        'preview_url': f'https://codesandbox.io/s/{sandbox_id}',
                        'embed_url': f'https://codesandbox.io/embed/{sandbox_id}'
                    }
                return {'success': False, 'error': 'Failed to create sandbox'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _generate_package_json(self, framework: str) -> str:
        """Generate package.json based on framework."""
        templates = {
            'react': '''{
  "name": "launchforge-preview",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  }
}''',
            'vue': '''{
  "name": "launchforge-preview",
  "version": "1.0.0",
  "dependencies": {
    "vue": "^3.3.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  }
}''',
            'nextjs': '''{
  "name": "launchforge-preview",
  "version": "1.0.0",
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "scripts": {
    "dev": "next dev",
    "build": "next build"
  }
}'''
        }
        return templates.get(framework, templates['react'])

    async def create_replit_preview(self, files: Dict[str, str], language: str = 'python3') -> Dict:
        """Create a Replit preview (generates shareable link)."""
        # Replit requires OAuth, so we generate a replit.nix config
        replit_config = '''run = "python main.py"
language = "python3"

[nix]
channel = "stable-23_05"

[deployment]
run = ["sh", "-c", "python main.py"]
'''

        files['replit.nix'] = replit_config

        return {
            'success': True,
            'files': files,
            'instructions': 'Import these files to Replit to preview',
            'replit_url': 'https://replit.com/new/python3'
        }

    async def generate_html_preview(self, files: Dict[str, str]) -> Dict:
        """Generate a static HTML preview that can be viewed in browser."""
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LaunchForge Preview</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .header { text-align: center; margin-bottom: 3rem; }
        .header h1 { font-size: 2.5rem; background: linear-gradient(135deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }
        .file-tree { background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; }
        .file-tree h3 { color: #3b82f6; margin-bottom: 1rem; }
        .file { padding: 0.5rem; background: #334155; margin: 0.5rem 0; border-radius: 6px; font-family: monospace; cursor: pointer; }
        .file:hover { background: #475569; }
        .code-preview { background: #1e293b; border-radius: 12px; padding: 1.5rem; }
        .code-preview h3 { color: #8b5cf6; margin-bottom: 1rem; }
        pre { background: #0f172a; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.875rem; }
        code { color: #a5f3fc; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Your App Preview</h1>
            <p>Generated by LaunchForge</p>
        </div>
        <div class="file-tree">
            <h3>📁 Project Files</h3>
'''

        for filename in files.keys():
            html_content += f'            <div class="file" onclick="showCode(\'{filename}\')">{filename}</div>\n'

        html_content += '''        </div>
        <div class="code-preview">
            <h3>📄 Code Preview</h3>
            <pre id="codeDisplay"><code>Select a file to view its contents</code></pre>
        </div>
    </div>
    <script>
        const files = ''' + str({k: v.replace('`', '\\`').replace('${', '\\${') for k, v in files.items()}) + ''';
        function showCode(filename) {
            document.getElementById('codeDisplay').innerHTML = '<code>' + (files[filename] || 'File not found').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</code>';
        }
    </script>
</body>
</html>'''

        return {
            'success': True,
            'html': html_content,
            'type': 'static_preview'
        }

    async def stop_preview(self, preview_id: str) -> Dict:
        """Stop an active preview."""
        if preview_id in self.active_previews:
            preview = self.active_previews.pop(preview_id)
            if 'process' in preview:
                preview['process'].terminate()
            return {'success': True, 'message': 'Preview stopped'}
        return {'success': False, 'error': 'Preview not found'}

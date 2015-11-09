from setuptools import setup

setup(
    name="Web Compiler",
    version="0.1",
    description="Web page templater",
    packages=['WebCompiler'],
    install_requires=[
        "jinja2",
        "Pillow",
    ],
    entry_points={"console_scripts": [
        "wc-html-cleanup=WebCompiler.htmlCleanup:cli",
        "wc-analyse=WebCompiler.siteAnalyse:cli",
        "wc-compile=WebCompiler.siteCompile:cli",
        "wc-fetch-images=WebCompiler.siteFetchImages:cli",
        "wc-process-logs=WebCompiler.siteProcessLogs:cli",
        "wc-watermark=WebCompiler.siteWatermark:cli",
    ]}
)

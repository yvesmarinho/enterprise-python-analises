"""
Enterprise Python Analysis - Main Entry Point

Este é o ponto de entrada principal do projeto.
Atualmente, os scripts principais estão em:
  - scripts/docker_analyzer.py - Análise de recursos Docker
  - scripts/generate_report.py - Geração de relatórios
  - scripts/docker_compose_ports_scanner.py - Scanner de portas

Para executar análises:
  python scripts/docker_analyzer.py
  python scripts/generate_report.py
"""


def main():
    print("🐳 Enterprise Python Analysis")
    print("\nScripts disponíveis:")
    print("  • python scripts/docker_analyzer.py - Análise de recursos Docker")
    print("  • python scripts/generate_report.py - Geração de relatórios")
    print("  • python scripts/docker_compose_ports_scanner.py - Scanner de portas")
    print("\nDocumentação: .docs/INDEX.md")


if __name__ == "__main__":
    main()

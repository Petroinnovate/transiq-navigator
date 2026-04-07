"""
Prompt Management CLI - Tool for managing prompt versions and performance analysis
"""
import sys
import argparse
from pathlib import Path
from tabulate import tabulate
from pipelines.prompts.loader import PromptLoader, get_loader
from pipelines.prompts.prompt_logger import PromptLogger, get_prompt_logger
from core.logging.logger import get_logger

logger = get_logger(__name__)


def list_prompts(args):
    """List all available prompts and their versions"""
    loader = get_loader()
    prompts_dir = loader.prompts_dir
    
    if not prompts_dir.exists():
        print(f"❌ Prompts directory not found: {prompts_dir}")
        return
    
    print(f"\n📂 Prompt Registry: {prompts_dir}\n")
    
    # Find all prompt directories
    prompt_dirs = [d for d in prompts_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    if not prompt_dirs:
        print("No prompts found.")
        return
    
    for prompt_dir in sorted(prompt_dirs):
        prompt_name = prompt_dir.name
        versions = loader.list_versions(prompt_name)
        
        if not versions:
            continue
        
        print(f"📝 {prompt_name}")
        
        # Load version details
        version_data = []
        for version in versions:
            try:
                prompt_version = loader.load_prompt(prompt_name, version)
                status = "✅ stable" if prompt_version.stable else "🚧 experimental"
                fallback = prompt_version.fallback_version or "none"
                desc = prompt_version.description[:60] + "..." if len(prompt_version.description) > 60 else prompt_version.description
                
                version_data.append([
                    version,
                    status,
                    fallback,
                    prompt_version.created_at,
                    desc
                ])
            except Exception as e:
                version_data.append([version, "❌ invalid", "-", "-", str(e)[:40]])
        
        headers = ["Version", "Status", "Fallback", "Created", "Description"]
        print(tabulate(version_data, headers=headers, tablefmt="simple"))
        print()


def show_prompt(args):
    """Show details of a specific prompt version"""
    loader = get_loader()
    
    try:
        prompt_version = loader.load_prompt(args.name, args.version)
        
        print(f"\n📝 Prompt: {prompt_version.name}")
        print(f"🏷️  Version: {prompt_version.version}")
        print(f"📅 Created: {prompt_version.created_at}")
        print(f"✅ Stable: {'Yes' if prompt_version.stable else 'No'}")
        if prompt_version.fallback_version:
            print(f"⬅️  Fallback: {prompt_version.fallback_version}")
        print(f"\n📄 Description:")
        print(f"   {prompt_version.description}")
        
        if prompt_version.metadata:
            print(f"\n🔧 Metadata:")
            for key, value in prompt_version.metadata.items():
                print(f"   {key}: {value}")
        
        print(f"\n📋 Template Preview (first 500 chars):")
        print(f"   {prompt_version.template[:500]}...")
        
        print(f"\n📁 File: {prompt_version.file_path}")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def performance_stats(args):
    """Show performance statistics for a prompt"""
    prompt_logger = get_prompt_logger()
    
    print(f"\n📊 Performance Statistics: {args.name}")
    if args.version:
        print(f"   Version: {args.version}")
    print(f"   Time window: {args.hours} hours\n")
    
    stats = prompt_logger.get_performance_stats(
        prompt_name=args.name,
        prompt_version=args.version,
        hours=args.hours
    )
    
    if "error" in stats:
        print(f"❌ {stats['error']}")
        return
    
    # Summary
    print(f"📈 Summary:")
    print(f"   Total executions: {stats['total_executions']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    
    # Latency
    print(f"\n⏱️  Latency:")
    latency = stats['latency']
    print(f"   Average: {latency['avg_ms']:.0f} ms")
    print(f"   Median (P50): {latency['p50_ms']:.0f} ms")
    print(f"   P95: {latency['p95_ms']:.0f} ms")
    print(f"   Min: {latency['min_ms']:.0f} ms")
    print(f"   Max: {latency['max_ms']:.0f} ms")
    
    # KPIs
    if stats['kpis']['avg_count'] > 0:
        print(f"\n📊 KPI Extraction:")
        kpis = stats['kpis']
        print(f"   Average count: {kpis['avg_count']:.1f}")
        print(f"   Min count: {kpis['min_count']}")
        print(f"   Max count: {kpis['max_count']}")


def register_ab_test(args):
    """Register an A/B test for a prompt"""
    loader = get_loader()
    
    versions = args.versions.split(',')
    weights = None
    if args.weights:
        weights = [float(w) for w in args.weights.split(',')]
        if len(weights) != len(versions):
            print(f"❌ Error: Number of weights ({len(weights)}) must match number of versions ({len(versions)})")
            return
        if abs(sum(weights) - 1.0) > 0.01:
            print(f"❌ Error: Weights must sum to 1.0 (current sum: {sum(weights)})")
            return
    
    try:
        loader.register_ab_test(args.name, versions, weights)
        print(f"✅ A/B test registered for '{args.name}'")
        print(f"   Versions: {versions}")
        if weights:
            print(f"   Weights: {weights}")
        else:
            equal_weight = 1.0 / len(versions)
            print(f"   Weights: Equal distribution ({equal_weight:.2f} each)")
    except Exception as e:
        print(f"❌ Error registering A/B test: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Prompt Management CLI - Manage prompt versions and analyze performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all prompts and versions
  python -m app.prompts.cli list

  # Show details of a specific prompt version
  python -m app.prompts.cli show dashboard --version 1.0.0

  # Show performance stats for last 24 hours
  python -m app.prompts.cli stats dashboard --hours 24

  # Show stats for specific version
  python -m app.prompts.cli stats dashboard --version 1.1.0 --hours 48

  # Register A/B test with equal weights
  python -m app.prompts.cli ab-test dashboard --versions 1.0.0,1.1.0

  # Register A/B test with custom weights (70/30 split)
  python -m app.prompts.cli ab-test dashboard --versions 1.0.0,1.1.0 --weights 0.7,0.3
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    parser_list = subparsers.add_parser('list', help='List all available prompts and versions')
    parser_list.set_defaults(func=list_prompts)
    
    # Show command
    parser_show = subparsers.add_parser('show', help='Show details of a specific prompt version')
    parser_show.add_argument('name', help='Prompt name (e.g., "dashboard")')
    parser_show.add_argument('--version', '-v', default='latest', help='Version (default: latest)')
    parser_show.set_defaults(func=show_prompt)
    
    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show performance statistics')
    parser_stats.add_argument('name', help='Prompt name')
    parser_stats.add_argument('--version', '-v', help='Specific version (optional, default: all versions)')
    parser_stats.add_argument('--hours', type=int, default=24, help='Time window in hours (default: 24)')
    parser_stats.set_defaults(func=performance_stats)
    
    # A/B test command
    parser_ab = subparsers.add_parser('ab-test', help='Register A/B test for a prompt')
    parser_ab.add_argument('name', help='Prompt name')
    parser_ab.add_argument('--versions', '-v', required=True, help='Comma-separated versions (e.g., "1.0.0,1.1.0")')
    parser_ab.add_argument('--weights', '-w', help='Comma-separated weights (e.g., "0.7,0.3", must sum to 1.0)')
    parser_ab.set_defaults(func=register_ab_test)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()

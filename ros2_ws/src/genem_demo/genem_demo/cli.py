"""ROS 2 console entry point, also runnable without ROS via python -m."""
import argparse
import json
from pathlib import Path
from genem_hsr.behavior import BehaviorError, parse_behavior
from genem_hsr.generator import APIBehaviorGenerator, OfflineGenerator, SCENARIOS
from genem_hsr.executor import BehaviorExecutor
from genem_hsr.history import record_history
from genem_hsr.skills import MockRobotSkillInterface, HSRRobotSkillInterface, HardwareDisabledError


def main(argv=None):
    parser = argparse.ArgumentParser(description='GenEM-inspired mock behavior demo')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--mock', action='store_true', help='default: record mock actions only')
    mode.add_argument('--hsr', action='store_true', help='disabled until hardware integration is verified')
    parser.add_argument('--backend', choices=['offline', 'api'], default='offline')
    parser.add_argument('--scenario', choices=list(SCENARIOS))
    parser.add_argument('--instruction')
    parser.add_argument('--behavior-file', type=Path)
    parser.add_argument('--feedback', help='one noninteractive feedback revision')
    parser.add_argument('--yes', action='store_true', help='execute in mock without prompting')
    parser.add_argument('--log', type=Path, default=Path.home() / 'genem_logs' / 'history.jsonl')
    args = parser.parse_args(argv)
    try:
        # Hardware disabled before any generation, API call, or input.
        adapter = HSRRobotSkillInterface() if args.hsr else MockRobotSkillInterface()
        generator = APIBehaviorGenerator() if args.backend == 'api' else OfflineGenerator()
        interactive = not (args.instruction or args.scenario or args.behavior_file)
        instruction = args.instruction or SCENARIOS.get(args.scenario)
        if args.behavior_file:
            instruction = instruction or 'Load supplied behavior'
            plan = parse_behavior(args.behavior_file.read_text(encoding='utf-8'))
        else:
            if interactive:
                if args.backend == 'offline':
                    print('Offline demo (rule-based). Examples: hello, Nod., Shake your head., '
                          'Become attentive., Acknowledge the person., Pay attention to the person.')
                while True:
                    instruction = input('Instruction (quit to exit):\n> ').strip()
                    if instruction.lower() in ('quit', 'exit'):
                        return 0
                    try:
                        plan = generator.generate(instruction)
                        break
                    except BehaviorError as exc:
                        if args.backend != 'offline':
                            raise
                        print(f'Unsupported input: {exc}')
                        print('Try: hello, Nod., Shake your head., Become attentive., '
                              'Acknowledge the person., or Pay attention to the person.')
            else:
                plan = generator.generate(instruction)
        print(f'Backend: {args.backend}; adapter: MOCK (no physical motion)')
        while True:
            print('Generated behavior:\n' + json.dumps(plan, indent=2))
            execute = args.yes or input('Execute MOCK? [y/N] ').strip().lower() == 'y'
            if execute:
                BehaviorExecutor(adapter).execute(plan)
            feedback = args.feedback
            if feedback is None and interactive:
                feedback = input('Feedback (empty to finish):\n> ').strip()
            if not feedback:
                record_history(args.log, instruction, plan, executed=execute, backend=args.backend)
                break
            updated = generator.generate(instruction, previous=plan, feedback=feedback)
            record_history(args.log, instruction, plan, feedback, updated,
                           executed=execute, backend=args.backend)
            plan = updated
            args.feedback = None
            if not interactive:
                print('Updated behavior:\n' + json.dumps(plan, indent=2))
                update_execute = args.yes or input('Execute updated MOCK? [y/N] ').strip().lower() == 'y'
                if update_execute:
                    BehaviorExecutor(adapter).execute(plan)
                record_history(args.log, instruction, plan, executed=update_execute, backend=args.backend)
                break
        return 0
    except (BehaviorError, HardwareDisabledError, OSError) as exc:
        print(f'Error: {exc}')
        return 2
    except (EOFError, KeyboardInterrupt):
        print('\nDemo stopped.')
        return 130


if __name__ == '__main__':
    raise SystemExit(main())

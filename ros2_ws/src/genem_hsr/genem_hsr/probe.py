"""Read-only controller / joint-state connectivity check; never sends a motion goal."""
import argparse
import json
from .behavior import BehaviorError
from .skills import HSRRobotSkillInterface, HardwareDisabledError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    args = parser.parse_args(argv)
    adapter = None
    try:
        from .head_motion import load_profile
        profile = load_profile(args.profile)
        adapter = HSRRobotSkillInterface(args.profile, mode=profile.environment, read_only=True)
        print(json.dumps(adapter.inspect(), indent=2))
        print('Read-only preflight passed. No motion goal sent.')
        return 0
    except (BehaviorError, HardwareDisabledError, OSError) as exc:
        print(f'Preflight failed: {exc}')
        return 2
    except (EOFError, KeyboardInterrupt):
        return 130
    finally:
        if adapter is not None:
            adapter.close()


if __name__ == '__main__':
    raise SystemExit(main())

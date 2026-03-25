import json
import time
import logging
import threading
import datetime as dt

from sqlalchemy.exc import IntegrityError

from rga_etl.databases.utils import init_session, init_instrument
from rga_etl.databases.mysql import Execution, PvsTScan, PvsTScanPoint
from rga_etl.pc_plc.http_handlers.shared import (
    DEFAULT_TIMEOUT,
    INIT_COMMANDS,
    END_COMMANDS,
    PARAM_COMMANDS,
    fill_execution_params,
)


class ScanState:
    def __init__(self):
        self._scan_thread = None
        self._stop_scan = threading.Event()

    def is_running(self):
        return self._scan_thread is not None and self._scan_thread.is_alive()

    def start(
        self,
        runner,
        masses,
        total_time,
        time_interval,
        publish_topic_prefix,
        subscribe_topic_prefix,
    ):
        self._stop_scan.clear()
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            args=(
                runner,
                masses,
                total_time,
                time_interval,
                publish_topic_prefix,
                subscribe_topic_prefix,
            ),
            daemon=True,
        )
        self._scan_thread.start()

    def _scan_loop(
        self,
        runner,
        masses,
        total_time,
        time_interval,
        publish_topic_prefix,
        subscribe_topic_prefix,
    ):
        def run_commands(commands):
            decorated = [
                {"publish": publish_topic_prefix, "subscribe": subscribe_topic_prefix, **cmd}
                for cmd in commands
            ]
            return runner.run_commands(decorated)

        n_cycles = int(total_time / time_interval)
        sorted_masses = sorted(masses)
        logging.info(
            f"Scan started — masses={sorted_masses}, total_time={total_time}s, "
            f"interval={time_interval}s, cycles={n_cycles}"
        )

        try:
            run_commands(INIT_COMMANDS)
            param_results = run_commands(PARAM_COMMANDS)

            started_at = dt.datetime.utcnow()
            scan_start = time.time()
            scan_points = []

            for i in range(n_cycles):
                if self._stop_scan.is_set():
                    break

                cycle_start = time.time()
                cycle_time = cycle_start - scan_start
                logging.info(f"Cycle {i + 1}/{n_cycles} — measuring masses {sorted_masses}")

                for mass in sorted_masses:
                    responses = run_commands(
                        [
                            {
                                "rga/command": f"MR{mass}\r",
                                "nocommand": 0,
                                "noresponse": 0,
                                "length": 4,
                                "timeout": DEFAULT_TIMEOUT,
                            }
                        ]
                    )
                    scan_points.append(
                        PvsTScanPoint(mass=mass, time=cycle_time, intensity=responses[0])
                    )

                elapsed = time.time() - cycle_start
                if elapsed > time_interval:
                    logging.warning(
                        f"Cycle {i + 1} took {elapsed:.1f}s, "
                        f"longer than interval {time_interval}s"
                    )
                else:
                    self._stop_scan.wait(timeout=time_interval - elapsed)

            run_commands(END_COMMANDS)
        except TimeoutError as e:
            logging.error(f"Scan aborted: {e}")
            return

        ended_at = dt.datetime.utcnow()
        total_elapsed = time.time() - scan_start
        if total_elapsed > total_time:
            logging.warning(
                f"Scan took {total_elapsed:.1f}s, longer than assigned total_time {total_time}s"
            )

        Session = init_session()
        with Session() as session:
            instrument = init_instrument(session)
            execution = Execution(instrument_id=instrument.id)
            fill_execution_params(execution, param_results)
            session.add(execution)
            session.flush()

            scan = PvsTScan(
                execution_id=execution.id,
                started_at=started_at,
                ended_at=ended_at,
                total_time=total_time,
                time_interval=time_interval,
            )
            session.add(scan)
            session.flush()

            for point in scan_points:
                point.scan_id = scan.id
            session.bulk_save_objects(scan_points)
            execution.end()
            try:
                session.commit()
            except IntegrityError:
                session.rollback()

        logging.info("Scan loop finished.")

    def stop(self):
        self._stop_scan.set()


scan_state = ScanState()


def handle_p_vs_t_scan(req, data, publish, subscribe):
    try:
        masses = data["MR"]
        total_time = float(data["TOTALTIME"])
        time_interval = float(data["TIMEINTERVAL"])
        if not isinstance(masses, list) or len(masses) == 0:
            raise ValueError("MR must be a non-empty list of masses")
    except (KeyError, ValueError) as e:
        req._reject(400, str(e))
        return

    scan_state.start(
        req.runner,
        masses,
        total_time,
        time_interval,
        publish,
        subscribe,
    )

    req._set_headers(200)
    req.wfile.write(
        json.dumps(
            {
                "status": "ok",
                "message": f"Scan started for masses {masses}",
            }
        ).encode()
    )

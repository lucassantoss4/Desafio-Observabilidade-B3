import http from 'k6/http';
import { check, sleep } from 'k6';

const vus = Number(__ENV.K6_VUS || 50);
const duration = __ENV.K6_DURATION || '5m';
const baseUrl = __ENV.BASE_URL || 'http://api:8000';

export const options = {
  vus,
  duration,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const response = http.get(
    `${baseUrl}/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2`
  );

  check(response, {
    'status is 200': (r) => r.status === 200,
    'authorized is true': (r) => r.json('authorized') === true,
    'resolution exists': (r) => Boolean(r.json('resolution')),
  });

  sleep(0.1);
}

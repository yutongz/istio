// Copyright 2017 Istio Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"flag"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"istio.io/fortio/fhttp"
	"istio.io/fortio/periodic"
	"fmt"
)

const (
	fetchInterval = 10
)

var (
	webAddress = flag.String("listen_port", ":9103", "Port on which to expose metrics and web interface.")

	metricsSuite *p8sMetricsSuite

	//gcsClient  *storage.Client
	//httpClient = &http.Client{}
)

type p8sMetricsSuite struct {
	succReqs       *prometheus.GaugeVec
	badReqs        *prometheus.GaugeVec
	actualDuration *prometheus.GaugeVec
	averageLatency *prometheus.GaugeVec
}

func newP8sMetricsSuite() *p8sMetricsSuite {
	return &p8sMetricsSuite{
		succReqs: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "successful_request_count",
				Help: "Successful Request Count",
			},
			[]string{"prod_env", "qps", "num_thread", "duration", "protocol"},
		),

		badReqs: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "failed_request_count",
				Help: "Failed Request Count",
			},
			[]string{"prod_env", "qps", "num_thread", "duration", "protocol"},
		),

		actualDuration: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "actual_duration",
				Help: "Actual Duration",
			},
			[]string{"prod_env", "qps", "num_thread", "duration", "protocol"},
		),

		averageLatency: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "average_latency",
				Help: "Average Latency",
			},
			[]string{"prod_env", "qps", "num_thread", "duration", "protocol"},
		),
	}
}

func init() {
	metricsSuite = newP8sMetricsSuite()
	metricsSuite.registerMetricVec()
}

func main() {
	flag.Parse()

	go func() {
		for {
			url := "http://127.0.0.1:8080"
			opts := fhttp.HTTPRunnerOptions{
				RunnerOptions: periodic.RunnerOptions{
					QPS:        10,
					Duration:   1 * time.Minute,
					NumThreads: 8,
				},
				URL: url,
				DisableFastClient: true,
			}

			loadHttpRequests(opts)

			time.Sleep(time.Duration(fetchInterval) * time.Minute)
		}
	}()

	http.Handle("/metrics", promhttp.Handler())
	log.Print(http.ListenAndServe(*webAddress, nil))
}

func (m *p8sMetricsSuite) registerMetricVec() {
	prometheus.MustRegister(m.succReqs)
	prometheus.MustRegister(m.badReqs)
	prometheus.MustRegister(m.actualDuration)
	prometheus.MustRegister(m.averageLatency)
}

func loadHttpRequests(opts fhttp.HTTPRunnerOptions) error {

	res, err := fhttp.RunHTTPTest(&opts)
	if err != nil {
		log.Printf("Generating traffic via fortio failed")
		return err
	}

	fmt.Printf("avg: %f", res.Result().DurationHistogram.Avg)

	metricsSuite.succReqs.
		WithLabelValues("release-0.2", strconv.Itoa(int(opts.QPS)), strconv.Itoa(int(opts.NumThreads)), opts.Duration.String(), "http").
		Set(float64(res.RetCodes[http.StatusOK]))
	metricsSuite.badReqs.
		WithLabelValues("release-0.2", strconv.Itoa(int(opts.QPS)), strconv.Itoa(int(opts.NumThreads)), opts.Duration.String(), "http").
		Set(float64(res.RetCodes[http.StatusBadRequest]))
	metricsSuite.actualDuration.
		WithLabelValues("release-0.2", strconv.Itoa(int(opts.QPS)), strconv.Itoa(int(opts.NumThreads)), opts.Duration.String(), "http").
		Set(res.ActualDuration.Seconds())
	//metricsSuite.averageLatency.
	//	WithLabelValues("release-0.2", strconv.Itoa(int(opts.QPS)), strconv.Itoa(int(opts.NumThreads)), opts.Duration.String(), "http").
	//	Set(aveLatency)

	return nil
}

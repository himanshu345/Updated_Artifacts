// main_6sites.cpp -- 6-site website-fingerprinting trace collector (paper §VI).
//
// Faithful to scripts/main.cpp: for each site, launch Chrome loading the URL,
// sample the PP0/core RAPL energy counter every 1 ms for 1000 samples (a 1 s
// window), store the per-sample energy delta, kill Chrome, repeat. Output CSV
// matches the original layout (Sample_ID,Website,Trace_1..N,Mean,Variance).
//
// Differences from main.cpp, all required to re-run here, none affecting method:
//   * website list restricted to the 6 sites reported in the paper;
//   * trace count is argv[1] (default 300) instead of a hardcoded 10000;
//   * RAPL is root-only on this host, so the program runs as root and launches
//     Chrome as the desktop user (sudo -u) with that user's DISPLAY/XAUTHORITY.
//
// Build : g++ -O2 -o main_6sites main_6sites.cpp
// Run   : sudo ./main_6sites [num_traces]      (default 300)
#include <iostream>
#include <fstream>
#include <chrono>
#include <thread>
#include <vector>
#include <cstdlib>
#include <cmath>
#include <string>
#include <unistd.h>
#include <sys/types.h>
#include <signal.h>
#include <sys/wait.h>

#define RAPL_Package "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj"

// Desktop session of the agv user (uid 1000) -- where Chrome must appear.
#define DESK_USER  "agv"
#define DESK_DISPLAY "DISPLAY=:0"
#define DESK_XAUTH  "XAUTHORITY=/run/user/1000/gdm/Xauthority"

using namespace std;
using namespace std::chrono;

static int NUM_TRACES = 300;
static const int NUM_SAMPLES = 1000;   // 1000 x 1 ms = 1 s window (unchanged)

pid_t launch_chrome(const std::string& command) {
    pid_t pid = fork();
    if (pid == 0) {
        setpgid(0, 0);                                   // new process group
        execl("/bin/sh", "sh", "-c", command.c_str(), (char*) nullptr);
        _exit(1);
    }
    return pid;
}

long read_rapl(const char* filename) {
    ifstream file(filename);
    long energy = 0;
    if (file.is_open()) { file >> energy; file.close(); }
    else cerr << "Failed to read RAPL file: " << filename << endl;
    return energy;
}

void measure_power(const string& website, const string& url) {
    cout << "Opening website: " << website << endl;
    vector<vector<long>> traces(NUM_TRACES, vector<long>(NUM_SAMPLES, 0));

    for (int trace = 0; trace < NUM_TRACES; ++trace) {
        std::string user_profile = "/tmp/guest-profile-" + std::to_string(trace);
        // Launch Chrome as the desktop user on the live :0 session.
        std::string chrome_cmd =
            "sudo -u " DESK_USER " env " DESK_DISPLAY " " DESK_XAUTH " "
            "google-chrome --incognito --no-first-run --no-default-browser-check "
            "--disable-gpu --disable-software-rasterizer "
            "--disable-features=VizDisplayCompositor "
            "--user-data-dir=" + user_profile + " " + url +
            " >/dev/null 2>&1";

        std::cout << "  trace " << trace << "/" << NUM_TRACES << "\r" << std::flush;
        pid_t chrome_pid = launch_chrome(chrome_cmd);

        long prev_energy = read_rapl(RAPL_Package);
        auto start_time = high_resolution_clock::now();
        for (int i = 0; i < NUM_SAMPLES; ++i) {
            long curr_energy = read_rapl(RAPL_Package);
            traces[trace][i] = curr_energy - prev_energy;
            prev_energy = curr_energy;
            this_thread::sleep_until(start_time + microseconds(1000 * (i + 1)));
        }

        killpg(chrome_pid, SIGKILL);
        waitpid(chrome_pid, nullptr, 0);
        std::string cleanup = "rm -rf " + user_profile;
        if (system(cleanup.c_str()) != 0) { /* ignore */ }
        this_thread::sleep_for(seconds(2));
    }
    cout << endl;

    // zero-fill repair (carry forward) -- identical to original
    for (int trace = 0; trace < NUM_TRACES; ++trace)
        for (int j = 1; j < NUM_SAMPLES; ++j)
            if (traces[trace][j] == 0) traces[trace][j] = traces[trace][j - 1];

    vector<long>   mean_trace(NUM_SAMPLES, 0);
    vector<double> variance_trace(NUM_SAMPLES, 0.0);
    for (int i = 0; i < NUM_SAMPLES; ++i) {
        long sum = 0;
        for (int t = 0; t < NUM_TRACES; ++t) sum += traces[t][i];
        mean_trace[i] = sum / NUM_TRACES;
        double vs = 0.0;
        for (int t = 0; t < NUM_TRACES; ++t) vs += pow(traces[t][i] - mean_trace[i], 2);
        variance_trace[i] = vs / NUM_TRACES;
    }

    string csv_filename = website + "_power_traces.csv";
    ofstream csv(csv_filename);
    if (!csv.is_open()) { cerr << "Failed to open " << csv_filename << endl; return; }
    csv << "Sample_ID,Website";
    for (int i = 1; i <= NUM_TRACES; ++i) csv << ",Trace_" << i;
    csv << ",Mean,Variance\n";
    for (int i = 0; i < NUM_SAMPLES; ++i) {
        csv << i << "," << website;
        for (int t = 0; t < NUM_TRACES; ++t) csv << "," << traces[t][i];
        csv << "," << mean_trace[i] << "," << variance_trace[i] << "\n";
    }
    csv.close();
    cout << "Finished " << website << " -> " << csv_filename << endl;
}

int main(int argc, char** argv) {
    if (argc > 1) NUM_TRACES = atoi(argv[1]);
    if (NUM_TRACES <= 0) NUM_TRACES = 300;
    cout << "num_traces per site = " << NUM_TRACES << endl;

    // the 6 sites reported in the paper (names match the existing CSV files)
    vector<pair<string,string>> websites = {
        {"Amazon.com",    "https://www.amazon.com"},
        {"Facebook.com",  "https://www.facebook.com"},
        {"Google.com",    "https://www.google.com"},
        {"Instagram.com", "https://www.instagram.com"},
        {"Wikipedia.org", "https://www.wikipedia.org"},
        {"Youtube.com",   "https://www.youtube.com"},
    };
    for (const auto& [w, u] : websites) measure_power(w, u);
    cout << "All 6 websites measured." << endl;
    return 0;
}

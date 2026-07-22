# entity-license-analysis

- license-entity-summary      output daily entity usage for a single tenant to a CSV file
- license-entity-analysis     output daily entity and volume usage, along with volume-per-entity statisics to xdr connector or CSV file (-o)

1. Clone this project on a target machine running docker
   
    `git clone https://github.com/stellarcyber-cse/entity-license-analysis.git`

2. Edit the config file
   
3. Install the requirements

    `pip install --no-cache-dir -r requirements.txt`

4. Run
   
   ```
   python license-entity-summary.py -t <tenant_id> [-c <config file>] [-l <log file>] [-d]

      usage: consume daily entity usage, summarize usage per day for unlimited number of days                                                                                                           
      options:
        -h, --help            show this help message and exit
        -c, --config YAML_CONFIG
                              use yaml config (default: config.yaml)
        -l, --log-file LOGFILE
                              Write stdout to logfile
        -d, --debug           Turn on debug/verbose logging
        -t, --tenant-id TENANT_ID
                              required tenant id
   ```

   ```
   python license-entity-analysis.py [-c <config file>] [-l <log file>] [-d] [-o | --csv-outfile]

      usage:    consume daily entity usage and break out entities by type (IP vs. User).
      
      options:
        -h, --help            show this help message and exit
        -c, --config YAML_CONFIG
                              use yaml config (default: config.yaml)
        -l, --log-file LOGFILE
                              Write stdout to logfile
        -d, --debug           Turn on debug/verbose logging
        -o, --csv-outfile     write out to CSV file instead of webhook
  ```

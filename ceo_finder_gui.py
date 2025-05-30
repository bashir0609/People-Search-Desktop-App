import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import pandas as pd
from pathlib import Path
import json
import sys

# Import your existing CEO finder
from people import CEOFinder, load_api_keys_from_env, check_dependencies

class CEOFinderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 CEO Finder Pro")
        self.root.geometry("800x700")
        self.root.minsize(750, 650)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Variables
        self.csv_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.processing_mode = tk.StringVar(value="empty_only")
        self.is_processing = False
        self.ceo_finder = None
        
        # Queue for thread communication
        self.message_queue = queue.Queue()
        
        # Create GUI
        self.create_widgets()
        
        # Start message checker
        self.check_messages()
        
        # Load API keys on startup
        self.load_api_keys()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🚀 CEO Finder Pro", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File Selection Section
        file_frame = ttk.LabelFrame(main_frame, text="📁 File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        # CSV File Selection
        ttk.Label(file_frame, text="CSV File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(file_frame, textvariable=self.csv_file_path, state="readonly").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(file_frame, text="Browse...", command=self.browse_csv_file).grid(row=0, column=2)
        
        # Output File
        ttk.Label(file_frame, text="Output File:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        ttk.Entry(file_frame, textvariable=self.output_file_path, state="readonly").grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=(10, 0))
        ttk.Button(file_frame, text="Set Output...", command=self.set_output_file).grid(row=1, column=2, pady=(10, 0))
        
        # Processing Mode Section
        mode_frame = ttk.LabelFrame(main_frame, text="⚙️ Processing Mode", padding="10")
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="🎯 Process ONLY missing CEOs (Recommended)", 
                       variable=self.processing_mode, value="empty_only").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="➡️ Continue from where left off", 
                       variable=self.processing_mode, value="continue").grid(row=1, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="🔄 Process all companies (Start over)", 
                       variable=self.processing_mode, value="new").grid(row=2, column=0, sticky=tk.W)
        
        # API Status Section
        api_frame = ttk.LabelFrame(main_frame, text="🔑 API Status", padding="10")
        api_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        api_frame.columnconfigure(0, weight=1)
        
        self.api_status_text = tk.Text(api_frame, height=4, state="disabled", font=("Consolas", 9))
        self.api_status_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        api_scrollbar = ttk.Scrollbar(api_frame, orient="vertical", command=self.api_status_text.yview)
        api_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.api_status_text.configure(yscrollcommand=api_scrollbar.set)
        
        ttk.Button(api_frame, text="🔄 Refresh API Status", command=self.load_api_keys).grid(row=1, column=0, pady=(10, 0))
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="📊 Progress", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to start processing...")
        self.progress_label.grid(row=1, column=0, sticky=tk.W)
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="🚀 Start Processing", command=self.start_processing, style="Accent.TButton")
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stop", command=self.stop_processing, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        self.results_button = ttk.Button(button_frame, text="📊 View Results", command=self.view_results, state="disabled")
        self.results_button.grid(row=0, column=2, padx=(0, 10))
        
        self.analyze_button = ttk.Button(button_frame, text="📈 Analyze", command=self.analyze_results, state="disabled")
        self.analyze_button.grid(row=0, column=3)
        
        # Log Section
        log_frame = ttk.LabelFrame(main_frame, text="📝 Live Log", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief="sunken", font=("Arial", 9))
        status_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def log_message(self, message, level="INFO"):
        """Add message to log display"""
        self.log_text.config(state="normal")
        
        # Color coding for different levels
        if level == "ERROR":
            color = "red"
        elif level == "SUCCESS":
            color = "green"
        elif level == "WARNING":
            color = "orange"
        else:
            color = "black"
        
        # Insert message with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        
        # Auto-scroll to bottom
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        
        # Update status bar
        self.status_var.set(message[:80] + "..." if len(message) > 80 else message)
    
    def browse_csv_file(self):
        """Browse for CSV file"""
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.csv_file_path.set(file_path)
            
            # Auto-set output file path
            output_path = file_path.replace('.csv', '_with_ceos.csv')
            self.output_file_path.set(output_path)
            
            # Analyze CSV
            self.analyze_csv_file(file_path)
            
            self.log_message(f"Selected CSV: {os.path.basename(file_path)}", "SUCCESS")
    
    def set_output_file(self):
        """Set output file path"""
        file_path = filedialog.asksaveasfilename(
            title="Set Output File",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.output_file_path.set(file_path)
            self.log_message(f"Output file set: {os.path.basename(file_path)}", "SUCCESS")
    
    def analyze_csv_file(self, file_path):
        """Analyze the selected CSV file"""
        try:
            df = pd.read_csv(file_path)
            total_companies = len(df)
            
            # Check if CEO data already exists
            if 'ceo_name' in df.columns:
                has_valid_ceo = (df['ceo_name'].notna() & 
                               (df['ceo_name'] != 'Not found') & 
                               (df['ceo_name'] != '') & 
                               (df['ceo_name'] != 'Error'))
                found_count = has_valid_ceo.sum()
                missing_count = total_companies - found_count
                
                self.log_message(f"CSV Analysis: {total_companies} companies total")
                self.log_message(f"✅ {found_count} CEOs already found, ❌ {missing_count} missing")
                
                if missing_count == 0:
                    self.log_message("🎉 All companies already have CEO data!", "SUCCESS")
                elif missing_count > 0:
                    self.log_message(f"💡 Recommend using 'Process ONLY missing CEOs' mode", "INFO")
            else:
                self.log_message(f"CSV Analysis: {total_companies} companies, no CEO data yet")
                
        except Exception as e:
            self.log_message(f"Error analyzing CSV: {str(e)}", "ERROR")
    
    def load_api_keys(self):
        """Load and display API key status"""
        self.api_status_text.config(state="normal")
        self.api_status_text.delete(1.0, tk.END)
        
        try:
            # Check dependencies first
            if not check_dependencies():
                self.api_status_text.insert(tk.END, "❌ Missing required Python packages\n")
                self.api_status_text.insert(tk.END, "Install: pip install pandas requests openai python-dotenv\n")
                self.api_status_text.config(state="disabled")
                return
            
            # Load API keys
            api_keys = load_api_keys_from_env()
            
            if api_keys:
                self.api_status_text.insert(tk.END, f"✅ {len(api_keys)} API keys loaded:\n")
                for key_name in api_keys.keys():
                    self.api_status_text.insert(tk.END, f"  ✓ {key_name.title()}\n")
                
                # Initialize CEO finder
                self.ceo_finder = CEOFinder(api_keys)
                self.start_button.config(state="normal")
                
            else:
                self.api_status_text.insert(tk.END, "❌ No API keys found\n")
                self.api_status_text.insert(tk.END, "Create a .env file with at least OPENAI_API_KEY\n")
                self.start_button.config(state="disabled")
                
        except Exception as e:
            self.api_status_text.insert(tk.END, f"❌ Error loading API keys: {str(e)}\n")
            self.start_button.config(state="disabled")
        
        self.api_status_text.config(state="disabled")
    
    def start_processing(self):
        """Start CEO finding process"""
        # Validate inputs
        if not self.csv_file_path.get():
            messagebox.showerror("Error", "Please select a CSV file")
            return
        
        if not self.output_file_path.get():
            messagebox.showerror("Error", "Please set an output file path")
            return
        
        if not self.ceo_finder:
            messagebox.showerror("Error", "API keys not loaded. Please check your .env file")
            return
        
        # Confirm processing
        csv_file = os.path.basename(self.csv_file_path.get())
        mode_text = {
            "empty_only": "Process ONLY missing CEOs",
            "continue": "Continue from where left off", 
            "new": "Process all companies"
        }[self.processing_mode.get()]
        
        if not messagebox.askyesno("Confirm Processing", 
                                  f"Start processing {csv_file}?\n\nMode: {mode_text}"):
            return
        
        # Start processing in background thread
        self.is_processing = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.results_button.config(state="disabled")
        self.analyze_button.config(state="disabled")
        
        self.log_message("🚀 Starting CEO finding process...", "SUCCESS")
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self.process_companies, daemon=True)
        self.worker_thread.start()
    
    def process_companies(self):
        """Process companies in background thread"""
        try:
            # Custom processing based on mode
            csv_file = self.csv_file_path.get()
            output_file = self.output_file_path.get()
            mode = self.processing_mode.get()
            
            # Load CSV
            df = pd.read_csv(csv_file)
            total_companies = len(df)
            
            self.message_queue.put(("log", f"Loaded {total_companies} companies from CSV", "INFO"))
            
            # Determine which companies to process
            if mode == "empty_only":
                # Find companies with missing CEO data
                if 'ceo_name' not in df.columns:
                    df['ceo_name'] = ''
                
                has_valid_ceo = (df['ceo_name'].notna() & 
                               (df['ceo_name'] != 'Not found') & 
                               (df['ceo_name'] != '') & 
                               (df['ceo_name'] != 'Error'))
                
                companies_to_process = df[~has_valid_ceo].index.tolist()
                self.message_queue.put(("log", f"Found {len(companies_to_process)} companies missing CEO data", "INFO"))
                
            elif mode == "continue":
                # Find first unprocessed company
                if 'ceo_name' not in df.columns:
                    df['ceo_name'] = ''
                
                start_index = 0
                for idx, row in df.iterrows():
                    if pd.isna(row.get('ceo_name')) or row.get('ceo_name') in ['', 'Not found', 'Error']:
                        start_index = idx
                        break
                
                companies_to_process = list(range(start_index, len(df)))
                self.message_queue.put(("log", f"Continuing from company #{start_index + 1}", "INFO"))
                
            else:  # new
                companies_to_process = list(range(len(df)))
                self.message_queue.put(("log", f"Processing all {len(companies_to_process)} companies", "INFO"))
            
            # Initialize result columns
            result_columns = ['ceo_name', 'ceo_title', 'ceo_email', 'ceo_linkedin', 'confidence', 'source']
            for col in result_columns:
                if col not in df.columns:
                    df[col] = pd.Series(dtype='string')
                else:
                    df[col] = df[col].astype('string')
            
            # Detect company column
            company_col = None
            website_col = None
            for col in df.columns:
                col_lower = col.lower().strip()
                if not company_col and any(term in col_lower for term in ['company', 'business', 'name']):
                    company_col = col
                if not website_col and any(term in col_lower for term in ['website', 'web', 'url', 'domain']):
                    website_col = col
            
            if not company_col:
                raise ValueError("Could not find company name column in CSV")
            
            # Process companies
            processed_count = 0
            success_count = 0
            
            for i, index in enumerate(companies_to_process):
                if not self.is_processing:  # Check if user stopped
                    break
                
                row = df.iloc[index]
                company_name = str(row[company_col]).strip()
                
                if not company_name or company_name in ['nan', 'None']:
                    continue
                
                # Update progress
                progress = (i + 1) / len(companies_to_process) * 100
                self.message_queue.put(("progress", progress, f"Processing {i + 1}/{len(companies_to_process)}: {company_name}"))
                
                # Get website URL
                website_url = None
                if website_col and pd.notna(row[website_col]):
                    website_url = str(row[website_col]).strip()
                    if website_url and not website_url.startswith(('http://', 'https://')):
                        website_url = 'https://' + website_url
                
                # Find CEO using your existing methods
                ceo_info = self.ceo_finder.find_ceo_ultra_aggressive(company_name, website_url)
                
                # Update DataFrame
                df.at[index, 'ceo_name'] = str(ceo_info.get('ceo_name', ''))
                df.at[index, 'ceo_title'] = str(ceo_info.get('ceo_title', ''))
                df.at[index, 'ceo_email'] = str(ceo_info.get('ceo_email', ''))
                df.at[index, 'confidence'] = str(ceo_info.get('confidence', ''))
                df.at[index, 'source'] = str(ceo_info.get('source', ''))
                
                # Search LinkedIn if CEO found
                if self.ceo_finder._is_valid_result(ceo_info):
                    linkedin_url = self.ceo_finder.search_ceo_linkedin(ceo_info['ceo_name'], company_name)
                    df.at[index, 'ceo_linkedin'] = str(linkedin_url) if linkedin_url else ''
                    success_count += 1
                    self.message_queue.put(("log", f"✅ Found CEO for {company_name}: {ceo_info['ceo_name']}", "SUCCESS"))
                else:
                    df.at[index, 'ceo_linkedin'] = ''
                    self.message_queue.put(("log", f"❌ No CEO found for {company_name}", "WARNING"))
                
                processed_count += 1
                
                # Save progress every 5 companies
                if processed_count % 5 == 0:
                    df.to_csv(output_file, index=False)
                    self.message_queue.put(("log", f"💾 Progress saved ({processed_count} companies processed)", "INFO"))
            
            # Final save
            df.to_csv(output_file, index=False)
            
            if self.is_processing:  # Only show completion if not stopped
                self.message_queue.put(("complete", processed_count, success_count))
            
        except Exception as e:
            self.message_queue.put(("error", str(e), None))
    
    def stop_processing(self):
        """Stop the processing"""
        self.is_processing = False
        self.log_message("⏹️ Stopping process...", "WARNING")
        
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        if self.output_file_path.get() and os.path.exists(self.output_file_path.get()):
            self.results_button.config(state="normal")
            self.analyze_button.config(state="normal")
    
    def check_messages(self):
        """Check for messages from worker thread"""
        try:
            while True:
                message_type, data, extra = self.message_queue.get_nowait()
                
                if message_type == "log":
                    self.log_message(data, extra)
                elif message_type == "progress":
                    self.progress_var.set(data)
                    self.progress_label.config(text=extra)
                elif message_type == "complete":
                    self.processing_complete(data, extra)
                elif message_type == "error":
                    self.processing_error(data)
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_messages)
    
    def processing_complete(self, processed_count, success_count):
        """Handle processing completion"""
        self.is_processing = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.results_button.config(state="normal")
        self.analyze_button.config(state="normal")
        
        success_rate = (success_count / processed_count * 100) if processed_count > 0 else 0
        
        self.log_message("🎉 Processing completed!", "SUCCESS")
        self.log_message(f"📊 Results: {success_count}/{processed_count} CEOs found ({success_rate:.1f}%)", "SUCCESS")
        self.progress_label.config(text=f"Complete! {success_count}/{processed_count} CEOs found")
        
        messagebox.showinfo("Processing Complete", 
                          f"CEO finding completed!\n\n"
                          f"Processed: {processed_count} companies\n"
                          f"CEOs found: {success_count} ({success_rate:.1f}%)\n\n"
                          f"Results saved to: {os.path.basename(self.output_file_path.get())}")
    
    def processing_error(self, error_message):
        """Handle processing error"""
        self.is_processing = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        self.log_message(f"❌ Error: {error_message}", "ERROR")
        messagebox.showerror("Processing Error", f"An error occurred:\n\n{error_message}")
    
    def view_results(self):
        """Open results file"""
        if self.output_file_path.get() and os.path.exists(self.output_file_path.get()):
            try:
                # Try to open with default CSV viewer
                import subprocess
                import platform
                
                if platform.system() == "Windows":
                    os.startfile(self.output_file_path.get())
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", self.output_file_path.get()])
                else:  # Linux
                    subprocess.run(["xdg-open", self.output_file_path.get()])
                    
                self.log_message("📊 Opened results file", "SUCCESS")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not open results file:\n{str(e)}")
        else:
            messagebox.showwarning("No Results", "No results file found. Please run processing first.")
    
    def analyze_results(self):
        """Show results analysis window"""
        if not self.output_file_path.get() or not os.path.exists(self.output_file_path.get()):
            messagebox.showwarning("No Results", "No results file found. Please run processing first.")
            return
        
        try:
            # Create analysis window
            analysis_window = tk.Toplevel(self.root)
            analysis_window.title("📈 Results Analysis")
            analysis_window.geometry("600x500")
            
            # Load and analyze data
            df = pd.read_csv(self.output_file_path.get())
            total = len(df)
            
            has_valid_ceo = (df['ceo_name'].notna() & 
                           (df['ceo_name'] != 'Not found') & 
                           (df['ceo_name'] != '') & 
                           (df['ceo_name'] != 'Error'))
            found = has_valid_ceo.sum()
            missing = total - found
            
            # Create analysis text
            analysis_text = scrolledtext.ScrolledText(analysis_window, font=("Consolas", 10))
            analysis_text.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Generate analysis report
            report = f"""📊 CEO FINDER RESULTS ANALYSIS
{'='*50}

📈 OVERVIEW:
  Total companies: {total:,}
  CEOs found: {found:,} ({found/total*100:.1f}%)
  Missing CEO data: {missing:,} ({missing/total*100:.1f}%)

"""
            
            # Confidence breakdown
            if 'confidence' in df.columns and found > 0:
                report += "🎯 CONFIDENCE LEVELS:\n"
                confidence_counts = df[has_valid_ceo]['confidence'].value_counts()
                for conf, count in confidence_counts.items():
                    if conf and conf != '':
                        percentage = count/found*100
                        report += f"  {conf.title()}: {count:,} ({percentage:.1f}%)\n"
                report += "\n"
            
            # Source breakdown
            if 'source' in df.columns and found > 0:
                report += "🔍 SOURCES USED:\n"
                source_counts = df[has_valid_ceo]['source'].value_counts()
                for source, count in source_counts.head(8).items():
                    if source and source != '':
                        percentage = count/found*100
                        report += f"  {source}: {count:,} ({percentage:.1f}%)\n"
                report += "\n"
            
            # Contact info coverage
            if 'ceo_linkedin' in df.columns:
                has_linkedin = (df[has_valid_ceo]['ceo_linkedin'].notna() & 
                              (df[has_valid_ceo]['ceo_linkedin'] != ''))
                linkedin_count = has_linkedin.sum()
                linkedin_percentage = linkedin_count/found*100 if found > 0 else 0
                report += f"🔗 CONTACT INFO:\n"
                report += f"  LinkedIn profiles: {linkedin_count:,}/{found:,} ({linkedin_percentage:.1f}%)\n"
                
                if 'ceo_email' in df.columns:
                    has_email = (df[has_valid_ceo]['ceo_email'].notna() & 
                               (df[has_valid_ceo]['ceo_email'] != ''))
                    email_count = has_email.sum()
                    email_percentage = email_count/found*100 if found > 0 else 0
                    report += f"  Email addresses: {email_count:,}/{found:,} ({email_percentage:.1f}%)\n"
                report += "\n"
            
            # Sample results
            if found > 0:
                report += "✅ SAMPLE SUCCESSFUL RESULTS:\n"
                successful = df[has_valid_ceo].head(5)
                for idx, row in successful.iterrows():
                    company = row[df.columns[0]]
                    ceo = row['ceo_name']
                    title = row.get('ceo_title', 'CEO')
                    confidence = row.get('confidence', 'unknown')
                    report += f"  • {company} → {ceo} ({title}) [{confidence}]\n"
                report += "\n"
            
            # Recommendations
            if missing > 0:
                report += "💡 RECOMMENDATIONS:\n"
                report += f"  • {missing:,} companies still need CEO data\n"
                report += "  • Use 'Process ONLY missing CEOs' mode to retry failed cases\n"
                report += "  • Consider manual research for difficult cases\n"
                if missing < 10:
                    report += "  • With only a few missing, manual research might be efficient\n"
                else:
                    report += "  • Consider adding more API keys for better coverage\n"
            
            analysis_text.insert("1.0", report)
            analysis_text.config(state="disabled")
            
            # Add export button
            export_button = ttk.Button(analysis_window, text="📄 Export Analysis", 
                                     command=lambda: self.export_analysis(report))
            export_button.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Could not analyze results:\n{str(e)}")
    
    def export_analysis(self, report):
        """Export analysis report to text file"""
        file_path = filedialog.asksaveasfilename(
            title="Export Analysis Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                messagebox.showinfo("Export Complete", f"Analysis report exported to:\n{os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Could not export analysis:\n{str(e)}")

def main():
    """Main function to run the desktop app"""
    root = tk.Tk()
    
    # Set window icon (if available)
    try:
        # You can add an icon file here
        # root.iconbitmap("ceo_finder_icon.ico")
        pass
    except:
        pass
    
    app = CEOFinderGUI(root)
    
    # Handle window close
    def on_closing():
        if app.is_processing:
            if messagebox.askokcancel("Quit", "Processing is still running. Do you want to stop and quit?"):
                app.is_processing = False
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    main()
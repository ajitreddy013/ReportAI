class SmartReportGenerator {
  constructor() {
    this.currentStep = 1;
    this.totalSteps = 4;
    this.documentId = null;
    this.uploadedImages = [];
    this.analysisData = null;

    this.initializeEventListeners();
  }

  initializeEventListeners() {
    // Step navigation
    document
      .getElementById("analyzeBtn")
      ?.addEventListener("click", () => this.analyzeSample());
    document
      .getElementById("nextStep2")
      ?.addEventListener("click", () => this.nextStep());
    document
      .getElementById("prevStep2")
      ?.addEventListener("click", () => this.previousStep());
    document
      .getElementById("nextStep3")
      ?.addEventListener("click", () => this.nextStep());
    document
      .getElementById("prevStep3")
      ?.addEventListener("click", () => this.previousStep());
    document
      .getElementById("nextStep4")
      ?.addEventListener("click", () => this.nextStep());
    document
      .getElementById("prevStep4")
      ?.addEventListener("click", () => this.previousStep());
    document
      .getElementById("generateSmartBtn")
      ?.addEventListener("click", () => this.generateReport());

    // Image handling
    document
      .getElementById("include_images")
      ?.addEventListener("change", (e) => {
        const imageSection = document.getElementById("imageSection");
        imageSection.classList.toggle("hidden", !e.target.checked);
      });

    document.getElementById("image_files")?.addEventListener("change", (e) => {
      this.handleImageUpload(e.target.files);
    });

    // Gemini configuration
    document
      .getElementById("configureGeminiBtn")
      ?.addEventListener("click", () => this.configureGeminiAPI());

    // Sample file analysis
    document.getElementById("sample_file")?.addEventListener("change", () => {
      this.resetAnalysis();
    });

    // Real-time review updates
    document
      .getElementById("topic_smart")
      ?.addEventListener("input", () => this.updateReview());
    document
      .getElementById("student_name_smart")
      ?.addEventListener("input", () => this.updateReview());
    document
      .getElementById("convertToPdf_smart")
      ?.addEventListener("change", () => this.updateReview());
  }

  async analyzeSample() {
    const sampleFile = document.getElementById("sample_file");
    if (!sampleFile.files.length) {
      this.showStatus("Please select a sample document first.", "error");
      return;
    }

    this.showLoading(true, "Analyzing document format...");
    this.updateProgress(1, 25);

    const formData = new FormData();
    formData.append("sample_file", sampleFile.files[0]);

    try {
      const response = await fetch("http://localhost:8001/analyze-sample", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const analysis = await response.json();
      this.analysisData = analysis;
      this.documentId = analysis.document_id;

      this.displayAnalysisResults(analysis);
      this.updateProgress(1, 100);
      this.showStatus("Document analyzed successfully!", "success");
      this.showLoading(false);

      // Check Gemini API status
      this.checkGeminiStatus();

      // Auto-advance to next step
      setTimeout(() => this.nextStep(), 1500);
    } catch (error) {
      this.showStatus(`Analysis error: ${error.message}`, "error");
      this.showLoading(false);
    }
  }

  displayAnalysisResults(analysis) {
    const preview = document.getElementById("analysisPreview");
    preview.classList.remove("hidden");

    document.getElementById(
      "compatibilityScore"
    ).textContent = `${analysis.template_compatibility.toUpperCase()} (${Math.round(
      analysis.formatting_preservation_score
    )}%)`;
    document.getElementById("detectedSections").textContent =
      analysis.content_sections.join(", ") || "Standard sections";
    document.getElementById("formattingScore").textContent = `${Math.round(
      analysis.formatting_preservation_score
    )}%`;
  }

  resetAnalysis() {
    const preview = document.getElementById("analysisPreview");
    preview.classList.add("hidden");
    this.analysisData = null;
    this.documentId = null;
  }

  handleImageUpload(files) {
    this.uploadedImages = [];
    const imageList = document.getElementById("imageList");
    imageList.innerHTML = "";

    if (files.length === 0) return;

    // Upload images to server
    const formData = new FormData();
    for (let file of files) {
      formData.append("images", file);
    }

    this.showLoading(true, "Uploading images...");

    fetch("http://localhost:8001/upload-images", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        this.uploadedImages = data.uploaded_images || [];
        this.displayImageList();
        this.showLoading(false);
        this.showStatus(
          `${this.uploadedImages.length} images uploaded successfully!`,
          "success"
        );
      })
      .catch((error) => {
        this.showStatus(`Image upload failed: ${error.message}`, "error");
        this.showLoading(false);
      });
  }

  displayImageList() {
    const imageList = document.getElementById("imageList");
    imageList.innerHTML = "";

    this.uploadedImages.forEach((image, index) => {
      const imageItem = document.createElement("div");
      imageItem.className = "image-item";
      imageItem.innerHTML = `
                <div class="image-preview">
                    <span class="image-placeholder">🖼️</span>
                    <span class="image-name">${image.filename}</span>
                </div>
                <div class="image-controls">
                    <input type="text" class="caption-input" placeholder="Enter caption..." 
                           data-index="${index}">
                    <select class="section-select" data-index="${index}">
                        <option value="auto">Auto-place</option>
                        <option value="introduction">Introduction</option>
                        <option value="objectives">Objectives</option>
                        <option value="methodology">Methodology</option>
                        <option value="results">Results</option>
                        <option value="conclusion">Conclusion</option>
                    </select>
                </div>
            `;
      imageList.appendChild(imageItem);
    });
  }

  nextStep() {
    if (this.currentStep < this.totalSteps) {
      this.currentStep++;
      this.updateStepDisplay();
      this.updateProgress(
        this.currentStep,
        (this.currentStep / this.totalSteps) * 100
      );
    }
  }

  previousStep() {
    if (this.currentStep > 1) {
      this.currentStep--;
      this.updateStepDisplay();
      this.updateProgress(
        this.currentStep,
        (this.currentStep / this.totalSteps) * 100
      );
    }
  }

  updateStepDisplay() {
    // Hide all steps
    document.querySelectorAll(".step-content").forEach((step) => {
      step.classList.remove("active");
    });

    // Show current step
    document.getElementById(`step${this.currentStep}`).classList.add("active");

    // Update step indicators
    document.querySelectorAll(".step").forEach((step, index) => {
      step.classList.toggle("active", index + 1 <= this.currentStep);
      step.classList.toggle("completed", index + 1 < this.currentStep);
    });
  }

  updateProgress(step, percentage) {
    const progressFill = document.getElementById("progressFill");
    progressFill.style.width = `${percentage}%`;

    // Update step numbers
    document.querySelectorAll(".step").forEach((stepElement, index) => {
      const stepNum = index + 1;
      if (stepNum < step) {
        stepElement.classList.add("completed");
      } else if (stepNum === step) {
        stepElement.classList.add("active");
      } else {
        stepElement.classList.remove("active", "completed");
      }
    });
  }

  updateReview() {
    const topic = document.getElementById("topic_smart")?.value || "-";
    const student = document.getElementById("student_name_smart")?.value || "-";
    const images =
      this.uploadedImages.length > 0
        ? `${this.uploadedImages.length} images`
        : "None";
    const format = document.getElementById("convertToPdf_smart")?.checked
      ? "PDF"
      : "DOCX";

    document.getElementById("reviewTopic").textContent = topic;
    document.getElementById("reviewStudent").textContent = student;
    document.getElementById("reviewImages").textContent = images;
    document.getElementById("reviewFormat").textContent = format;
  }

  async generateReport() {
    if (!this.documentId) {
      this.showStatus("Please analyze a sample document first.", "error");
      return;
    }

    // Validate required fields
    const requiredFields = [
      "student_name_smart",
      "roll_no_smart",
      "topic_smart",
    ];
    for (let fieldId of requiredFields) {
      const field = document.getElementById(fieldId);
      if (!field.value.trim()) {
        this.showStatus(
          `Please fill in ${field.previousElementSibling.textContent}`,
          "error"
        );
        return;
      }
    }

    this.showLoading(true, "Generating your smart report...");
    this.updateProgress(4, 75);

    // Prepare image data
    const imageData = this.prepareImageData();

    // Prepare form data
    const formData = new FormData();
    formData.append("document_id", this.documentId);
    formData.append(
      "student_name",
      document.getElementById("student_name_smart").value
    );
    formData.append("roll_no", document.getElementById("roll_no_smart").value);
    formData.append("topic", document.getElementById("topic_smart").value);
    formData.append(
      "college_name",
      document.getElementById("college_name_smart").value
    );
    formData.append(
      "department",
      document.getElementById("department_smart").value
    );
    formData.append(
      "introduction",
      document.getElementById("introduction_smart").value
    );
    formData.append(
      "objectives",
      document.getElementById("objectives_smart").value
    );
    formData.append(
      "methodology",
      document.getElementById("methodology_smart").value
    );
    formData.append("result", document.getElementById("result_smart").value);
    formData.append(
      "conclusion",
      document.getElementById("conclusion_smart").value
    );
    formData.append(
      "references",
      document.getElementById("references_smart").value
    );
    formData.append("images_json", JSON.stringify(imageData));
    formData.append(
      "convert_to_pdf",
      document.getElementById("convertToPdf_smart").checked
    );
    formData.append(
      "content_style",
      document.getElementById("content_style").value
    );

    try {
      const response = await fetch(
        "http://localhost:8001/generate-smart-report",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`);
      }

      this.updateProgress(4, 100);
      this.showStatus("Report generated successfully!", "success");

      // Trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Smart_Report_${document
        .getElementById("student_name_smart")
        .value.replace(" ", "_")}_${
        document.getElementById("roll_no_smart").value
      }.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      this.showLoading(false);
    } catch (error) {
      this.showStatus(`Generation error: ${error.message}`, "error");
      this.showLoading(false);
    }
  }

  prepareImageData() {
    const imageData = [];
    const captionInputs = document.querySelectorAll(".caption-input");
    const sectionSelects = document.querySelectorAll(".section-select");

    captionInputs.forEach((input, index) => {
      const caption = input.value.trim();
      const section = sectionSelects[index].value;

      if (caption && this.uploadedImages[index]) {
        imageData.push({
          filename: this.uploadedImages[index].filename,
          caption: caption,
          content_relevance: section,
        });
      }
    });

    return imageData;
  }

  showStatus(message, type = "info") {
    const status = document.getElementById("status");
    status.textContent = message;
    status.className = `status-message ${type}`;
    status.classList.remove("hidden");

    // Auto-hide success messages
    if (type === "success") {
      setTimeout(() => {
        status.classList.add("hidden");
      }, 5000);
    }
  }

  showLoading(show, message = "") {
    const overlay = document.getElementById("loadingOverlay");
    const messageElement = overlay.querySelector("p");

    if (show) {
      messageElement.textContent = message;
      overlay.classList.remove("hidden");
    } else {
      overlay.classList.add("hidden");
    }
  }

  // Gemini API methods
  async checkGeminiStatus() {
    try {
      const response = await fetch("http://localhost:8001/gemini-status");
      const status = await response.json();
      
      const engineStatus = document.getElementById("engineStatus");
      const apiStatus = document.getElementById("apiStatus");
      
      if (engineStatus) {
        engineStatus.textContent = status.generation_status.primary_engine;
      }
      if (apiStatus) {
        apiStatus.textContent = status.configured ? "Configured" : "Not configured";
        apiStatus.className = `value ${status.configured ? "available" : "unavailable"}`;
      }
    } catch (error) {
      console.log("Could not check Gemini status:", error);
    }
  }

  async configureGeminiAPI() {
    const apiKey = prompt("Enter your Google Gemini API key:\n(Get it from: https://aistudio.google.com/app/apikey)");
    
    if (!apiKey) return;
    
    this.showLoading(true, "Configuring Gemini API...");
    
    try {
      const formData = new FormData();
      formData.append("api_key", apiKey);
      
      const response = await fetch("http://localhost:8001/configure-gemini", {
        method: "POST",
        body: formData
      });
      
      const result = await response.json();
      
      if (result.status === "success") {
        this.showStatus("Gemini API configured successfully!", "success");
        this.checkGeminiStatus(); // Refresh status
      } else {
        this.showStatus("Failed to configure Gemini API", "error");
      }
    } catch (error) {
      this.showStatus("Configuration error: " + error.message, "error");
    } finally {
      this.showLoading(false);
    }
  }
}

// Initialize the smart report generator when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  window.smartReportGenerator = new SmartReportGenerator();
});

.. _contact:

================================================================================
Contact & Feedback
================================================================================

We value your feedback on the Quantum Collider Sandbox! Use the form below to
report bugs, request features, or share any other thoughts about the simulation.

.. raw:: html

   <style>
     .feedback-form {
       max-width: 640px;
       margin: 1.5em 0;
       font-family: inherit;
     }
     .feedback-form .form-group {
       margin-bottom: 1.2em;
     }
     .feedback-form label {
       display: block;
       font-weight: bold;
       margin-bottom: 0.3em;
     }
     .feedback-form input[type="text"],
     .feedback-form input[type="email"],
     .feedback-form select,
     .feedback-form textarea {
       width: 100%;
       padding: 0.5em 0.6em;
       border: 1px solid #ccc;
       border-radius: 4px;
       font-size: 0.95em;
       box-sizing: border-box;
     }
     .feedback-form textarea {
       resize: vertical;
       min-height: 120px;
     }
     .feedback-form .required {
       color: #c00;
       margin-left: 0.2em;
     }
     .feedback-form button[type="submit"] {
       background-color: #2980b9;
       color: #fff;
       border: none;
       padding: 0.6em 1.4em;
       font-size: 1em;
       border-radius: 4px;
       cursor: pointer;
     }
     .feedback-form button[type="submit"]:hover {
       background-color: #1f6695;
     }
     .feedback-form .note {
       font-size: 0.85em;
       color: #555;
       margin-top: 0.3em;
     }
   </style>

   <!-- Replace the action URL with your own Formspree endpoint (https://formspree.io)
        or another form-handling service before deploying. -->
   <form
     class="feedback-form"
     action="https://formspree.io/f/contact-quantum-collider"
     method="POST"
   >
     <div class="form-group">
       <label for="fb-name">Name <span class="required">*</span></label>
       <input
         type="text"
         id="fb-name"
         name="name"
         placeholder="Your name"
         required
       />
     </div>

     <div class="form-group">
       <label for="fb-email">Email <span class="required">*</span></label>
       <input
         type="email"
         id="fb-email"
         name="email"
         placeholder="your@email.com"
         required
       />
       <p class="note">Your email will only be used to follow up on your feedback.</p>
     </div>

     <div class="form-group">
       <label for="fb-type">Feedback type <span class="required">*</span></label>
       <select id="fb-type" name="feedback_type" required>
         <option value="" disabled selected>— Select a category —</option>
         <option value="bug">Bug report</option>
         <option value="feature">Feature request</option>
         <option value="performance">Performance issue</option>
         <option value="documentation">Documentation improvement</option>
         <option value="general">General feedback</option>
       </select>
     </div>

     <div class="form-group">
       <label for="fb-message">Message <span class="required">*</span></label>
       <textarea
         id="fb-message"
         name="message"
         placeholder="Describe your feedback in detail…"
         required
       ></textarea>
     </div>

     <div class="form-group">
       <button type="submit">Send Feedback</button>
     </div>
   </form>

Other Ways to Reach Us
----------------------

- **GitHub Issues:** `<https://github.com/ml3m/quantum-collider-sandbox/issues>`_
- **GitHub Discussions:** `<https://github.com/ml3m/quantum-collider-sandbox/discussions>`_

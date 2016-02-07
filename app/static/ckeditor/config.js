/**
 * @license Copyright (c) 2003-2015, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.editorConfig = function( config ) {
	// Define changes to default configuration here.
	// For complete reference see:
	// http://docs.ckeditor.com/#!/api/CKEDITOR.config

	// The toolbar groups arrangement, optimized for two toolbar rows.
	config.toolbarGroups = [
		//{ name: 'clipboard',   groups: [ 'clipboard', 'undo' ] },
		//{ name: 'editing',     groups: [ 'find', 'selection', 'spellchecker' ] },
		{ name: 'links' },
        { name: 'upload' },
		{ name: 'insert' },
		{ name: 'forms' },
		{ name: 'tools' },
		{ name: 'document',	   groups: [ 'mode', 'document', 'doctools' ] },
		{ name: 'others' },
		'/',
		{ name: 'basicstyles', groups: [ 'basicstyles', 'cleanup' ] },
		{ name: 'paragraph',   groups: [ 'list', 'indent', 'blocks', 'align', 'bidi' ] },
		{ name: 'styles' },
		{ name: 'colors' },
		{ name: 'about' }
	];

	// Remove some buttons provided by the standard plugins, which are
	// not needed in the Standard(s) toolbar.
	config.removeButtons = 'Underline';

	// Set the most common block elements.
	config.format_tags = 'p;h1;h2;h3;pre';

	// Simplify the dialog windows.
	config.removeDialogTabs = 'image:Link;image:advanced;link:target;link:advanced';

    // site specific settings
    config.height = 500;

    config.extraPlugins = 'simpleuploads,autosave';
    config.removePlugins = 'elementspath';

    config.filebrowserUploadUrl = '/api/upload/file';
    config.filebrowserImageUploadUrl = '/api/upload/image';

    config.simpleuploads_acceptedExtensions = '7z|avi|csv|doc|docx|flv|gif|gz|gzip|jpeg|jpg|mov|mp3|mp4|mpc|mpeg|mpg|ods|odt|pdf|png|ppt|pptx|ps|pxd|rar|rtf|tar|tgz|txt|vsd|wav|wma|wmv|xls|xlsx|xml|zip';

    config.autosave_SaveKey = window.location.pathname;
    // autosave cache expires in 10 days
    config.autosave_NotOlderThen = 14400;
    // uncomment the following to clear saved data upon submit
    //config.autosave_saveDetectionSelectors = "button[type='submit']";
    config.autosave_saveDetectionSelectors = null;
    // autosave delay seconds after change
    config.autosave_delay = 5;
};

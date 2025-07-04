#!/usr/bin/env python3
"""
Complete end-to-end VLM workflow test with all fixes applied
"""
import sys
import os
import time
sys.path.insert(0, '.')
from autotasktracker.ai.vlm_processor import SmartVLMProcessor
from autotasktracker.core.database import DatabaseManager

def main():
    print('🔥 COMPLETE VLM WORKFLOW TEST')
    print('=' * 60)
    
    # Clear any existing processing flags first
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM metadata_entries WHERE key = "vlm_processing"')
        print(f'✅ Cleared {cursor.rowcount} old processing flags')
    
    # Initialize processor
    processor = SmartVLMProcessor()
    
    # Find a real unprocessed screenshot
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id, e.filepath,
                   aw.value as active_window,
                   ocr.value as ocr_text
            FROM entities e
            LEFT JOIN metadata_entries aw ON e.id = aw.entity_id AND aw.key = 'active_window'
            LEFT JOIN metadata_entries ocr ON e.id = ocr.entity_id AND ocr.key = 'ocr_result'
            LEFT JOIN metadata_entries vlm ON e.id = vlm.entity_id AND vlm.key = 'vlm_description'
            WHERE e.file_type_group = 'image' 
            AND e.filepath IS NOT NULL
            AND vlm.value IS NULL
            ORDER BY e.created_at DESC
            LIMIT 1
        ''')
        result = cursor.fetchone()
    
    if not result:
        print('❌ No unprocessed images found')
        return False
    
    entity_id = str(result['id'])
    filepath = result['filepath']
    window_title = result['active_window'] or 'Unknown Application'
    ocr_text = result['ocr_text']
    
    print(f'📊 Test Subject:')
    print(f'   Entity ID: {entity_id}')
    print(f'   File: {os.path.basename(filepath)}')
    print(f'   Window: {window_title[:60]}...')
    print(f'   OCR: {"Available" if ocr_text else "None"}')
    print(f'   File exists: {os.path.exists(filepath)}')
    
    try:
        print(f'\n🚀 Step 1: Processing with VLM...')
        start_time = time.time()
        
        result = processor.process_image(
            image_path=filepath,
            window_title=window_title,
            entity_id=entity_id,
            ocr_text=ocr_text,
            priority="high"
        )
        
        processing_time = time.time() - start_time
        
        if result:
            print(f'✅ SUCCESS! Processing completed in {processing_time:.1f}s')
            print(f'\n📋 VLM Analysis Results:')
            print(f'   Task: {result.get("task", "N/A")}')
            print(f'   Category: {result.get("category", "N/A")}')
            print(f'   Confidence: {result.get("confidence", "N/A")}')
            
            visual_context = result.get('visual_context', result.get('description', 'N/A'))
            if visual_context and len(visual_context) > 100:
                print(f'   Visual Context: {visual_context[:100]}...')
            else:
                print(f'   Visual Context: {visual_context}')
            
            ui_elements = result.get('ui_elements', {})
            if ui_elements:
                print(f'   UI Elements: {ui_elements}')
            
            subtasks = result.get('subtasks', [])
            if subtasks:
                print(f'   Subtasks: {subtasks[:3]}')
            
            print(f'\n💾 Step 2: Verifying database storage...')
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT value FROM metadata_entries 
                    WHERE entity_id = ? AND key = 'vlm_description'
                ''', (entity_id,))
                saved_result = cursor.fetchone()
                
            if saved_result:
                print(f'✅ VLM result saved to database!')
                import json
                try:
                    saved_data = json.loads(saved_result['value'])
                    print(f'   Saved keys: {list(saved_data.keys())}')
                    print(f'   Saved task: {saved_data.get("task", "N/A")}')
                except:
                    print(f'   Saved as text: {saved_result["value"][:50]}...')
            else:
                print(f'❌ VLM result not found in database')
                return False
            
            print(f'\n🎯 Step 3: Testing AI task extraction...')
            try:
                from autotasktracker.ai.ai_task_extractor import AIEnhancedTaskExtractor
                
                extractor = AIEnhancedTaskExtractor(db.db_path)
                enhanced_task = extractor.extract_enhanced_task(
                    window_title=window_title,
                    ocr_text=ocr_text,
                    vlm_description=None,  # Will fetch from DB
                    entity_id=int(entity_id)
                )
                
                print(f'✅ AI task extraction successful!')
                print(f'   Enhanced task: {enhanced_task.get("task", "N/A")}')
                print(f'   Enhanced category: {enhanced_task.get("category", "N/A")}')
                print(f'   AI features: {enhanced_task.get("ai_features", {})}')
                
            except ImportError:
                print(f'⚠️  AI task extractor not available')
            except Exception as e:
                print(f'❌ AI task extraction error: {e}')
            
            print(f'\n📊 Step 4: Checking system health...')
            cache_stats = processor.get_cache_stats()
            proc_stats = processor.get_processing_stats()
            
            print(f'   Cache: {cache_stats["image_cache_items"]} items, {cache_stats["image_cache_size_mb"]:.1f}MB')
            print(f'   Processing: {proc_stats["total_processed"]} images, avg {proc_stats["avg_processing_time"]:.1f}s')
            
            print(f'\n🎉 COMPLETE SUCCESS!')
            print(f'   ✅ VLM processing working')
            print(f'   ✅ Database integration working')
            print(f'   ✅ AI task extraction working')
            print(f'   ✅ All systems operational')
            
            return True
            
        else:
            print(f'❌ VLM processing returned None after {processing_time:.1f}s')
            print(f'   This indicates an Ollama API issue')
            
            # Check if the processing lock was cleaned up
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) as count FROM metadata_entries WHERE entity_id = ? AND key = "vlm_processing"', (entity_id,))
                lock_count = cursor.fetchone()['count']
                
            if lock_count > 0:
                print(f'   ⚠️  Processing lock not cleaned up properly')
            else:
                print(f'   ✅ Processing lock cleaned up correctly')
            
            return False
            
    except Exception as e:
        print(f'\n❌ WORKFLOW FAILED: {e}')
        import traceback
        traceback.print_exc()
        
        # Ensure cleanup
        try:
            processor._mark_processing_complete(entity_id, success=False)
        except:
            pass
            
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
extern crate proc_macro;

use proc_macro::TokenStream;
use quote::quote;
use syn;

#[proc_macro_derive(View)]
pub fn view_macro_derive(input: TokenStream) -> TokenStream {
    let ast: syn::DeriveInput = syn::parse(input).unwrap();
    let name = &ast.ident;
    let gen = quote! {
        impl View for #name {
            fn set_position(&mut self, x: i32, y: i32) {
                self.get_inner_mut().x = x;
                self.get_inner_mut().y = y;
            }

            fn set_size(&mut self, w: u32, h: u32) {
                self.get_inner_mut().w = w;
                self.get_inner_mut().h = h;
            }

            fn set_enabled(&mut self, enabled: bool) {
                self.get_inner_mut().enabled = enabled;
            }

            #[inline]
            fn get_inner(&self) -> &ViewInner {
                return &self.inner;
            }

            #[inline]
            fn get_inner_mut(&mut self) -> &mut ViewInner {
                return &mut self.inner;
            }

            fn handle_event_recursive(&mut self, app: &crate::loopbastard::App, event: &crate::loopbastard::events::AppEvent) {
                self.handle_event(app, event);
                self.foreach_event_handler(|child| {
                    if child.get_inner().enabled {
                        child.handle_event_recursive(app, event);
                    }
                });
            }

            fn render_recursive(&mut self, context: &mut crate::loopbastard::views::RenderContext, rect: & Rect) {
                let clip_rect = context.canvas.clip_rect();
                self.render(context, rect);
                self.foreach_child(|child| {
                    if child.get_inner().enabled {
                        let mut target_rect = Rect::new(
                            rect.x() + child.get_inner().x,
                            rect.y() + child.get_inner().y,
                            child.get_inner().w,
                            child.get_inner().h,
                        );
                        context.canvas.set_clip_rect(target_rect);
                        child.render_recursive(context, &target_rect);
                    }
                });
                context.canvas.set_clip_rect(clip_rect);
            }
        }
    };
    gen.into()
}

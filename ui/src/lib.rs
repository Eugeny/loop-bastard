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

            fn get_inner(&self) -> &ViewInner {
                return &self.inner;
            }

            fn get_inner_mut(&mut self) -> &mut ViewInner {
                return &mut self.inner;
            }

            fn render_recursive(&mut self, app: &mut App, canvas: &mut Canvas, rect: &Rect) {
                let clip_rect = canvas.clip_rect();
                self.render(app, canvas, rect);
                self.foreach_child(|child| {
                    let mut target_rect = Rect::new(
                        rect.x() + child.get_inner().x,
                        rect.y() + child.get_inner().y,
                        child.get_inner().w,
                        child.get_inner().h,
                    );
                    canvas.set_clip_rect(target_rect);
                    child.render_recursive(app, canvas, &target_rect);
                });
                canvas.set_clip_rect(clip_rect);
            }
        }
    };
    gen.into()
}
